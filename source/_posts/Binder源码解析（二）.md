---
title: Binder源码解析（二）
date: 2022-06-02 10:07:47
tags:
  - Android
  - FrameWork
  - Binder
---


# Binder源码解析（二）

### Binder系列传送门

[Android Framework Binder 总结](https://juejin.cn/post/7104338528439369758)

[Binder源码解析（一）](https://juejin.cn/post/7104343457610596360/)

[Binder源码解析（二）](https://juejin.cn/post/7104340048920707080)





### ServiceManager的启动流程

```c
system\core\roodir\init.rc：
service servicemanager /system/bin/servicemanager       //可知孵化器的目录为servicemanager
    class core
    user system
    group system
    critical
    onrestart restart healthd
    onrestart restart zygote
    onrestart restart media
    onrestart restart surfaceflinger
    onrestart restart drm
```

分析Android启动流程可知，Android启动时会解析init.rc，servicemanager 服务的孵化器的目录为/system/bin/servicemanager，在此目录下有service_manager.c、binder.c

<!--more-->



```c
frameworks\native\cmds\servicemanager\Service_manager.c：
int main(int argc, char **argv)
{
        struct binder_state *bs
    bs = binder_open(128*1024);         //1. 打开Binder驱动，建立128K = 128*1024内存映射
    if (binder_become_context_manager(bs)) {        //2. 设置自己（ServiceManager）为Binder的大管家
        ALOGE("cannot become context manager (%s)\n", strerror(errno));
        return -1;
    }
    ...
    svcmgr_handle = BINDER_SERVICE_MANAGER;
    binder_loop(bs, svcmgr_handler);            //3. 开启for循环，充当Server的角色，等待Client连接
    return 0;
}
```

分析binder_state：

```c
struct binder_state
{
    int fd;     //表示打开的/dev/binder文件句柄
    void *mapped;       //把设备文件/dev/binder映射到进程空间的起始地址
    size_t mapsize;     //内存映射空间的大小
};
```

分析BINDER_SERVICE_MANAGER：

```c
define BINDER_SERVICE_MANAGER  0U      //表示Service Manager的句柄为0
```

#### 1. binder_open

```c
frameworks/native/cmds/servicemanager/Binder.c：
struct binder_state *binder_open(size_t mapsize)
{
    struct binder_state *bs;
    struct binder_version vers;
    bs = malloc(sizeof(*bs));
    if (!bs) {
        errno = ENOMEM;
        return NULL;
    }
    bs->fd = open("/dev/binder", O_RDWR);               //调用Binder驱动注册的file_operation结构体的open、ioctl、mmap函数
    if (bs->fd < 0) {                                                       //a. binder_state.fd保存打开的/dev/binder文件句柄
        goto fail_open;
    }
    if ((ioctl(bs->fd, BINDER_VERSION, &vers) == -1) ||
        (vers.protocol_version != BINDER_CURRENT_PROTOCOL_VERSION)) {
        goto fail_open;
    }
    bs->mapsize = mapsize;          //b. binder_state.mapsize保存内存映射空间的大小128K = 128*1024
    bs->mapped = mmap(NULL, mapsize, PROT_READ, MAP_PRIVATE, bs->fd, 0);        //c. binder_state.mapped保存设备文件/dev/binder映射到进程空间的起始地址
    if (bs->mapped == MAP_FAILED) {
        fprintf(stderr,"binder: cannot map device (%s)\n",
                strerror(errno));
        goto fail_map;
    }
    return bs;
fail_map:
    close(bs->fd);
fail_open:
    free(bs);
    return NULL;
}
```

执行open(“/dev/binder”, O_RDWR);时从用户态进入内核态，因此会执行：

```c
drivers/staging/android/binder.c
static int binder_open(struct inode *nodp, struct file *filp)
{
    struct binder_proc *proc;
    proc = kzalloc(sizeof(*proc), GFP_KERNEL);      //a. 创建Service_manager进程对应的binder_proc，保存Service_manager进程的信息
    if (proc == NULL)
        return -ENOMEM;
    get_task_struct(current);
    proc->tsk = current;
    INIT_LIST_HEAD(&proc->todo);
    init_waitqueue_head(&proc->wait);
    proc->default_priority = task_nice(current);
    binder_lock(__func__);
    binder_stats_created(BINDER_STAT_PROC);
    hlist_add_head(&proc->proc_node, &binder_procs);        //binder_procs是一个全局变量，hlist_add_head是将proc->proc_node（proc->proc_node是一个hlist_node链表）加入binder_procs的list中
    proc->pid = current->group_leader->pid;
    INIT_LIST_HEAD(&proc->delivered_death);
    filp->private_data = proc;          //将binder_proc保存在打开文件file的私有数据成员变量private_data中
    binder_unlock(__func__);
    return 0;
}
```

在此函数中创建Service_manager进程对应的binder_proc，保存Service_manager进程的信息，并将binder_proc保存在打开文件file的私有数据成员变量private_data中

```c
//分析下面这个函数可以得出：函数功能是将proc->proc_node放入binder_procs链表的头部，注意是从右向左，最开始插入的binder_proc在binder_procs链表的最右边
static inline void hlist_add_head(struct hlist_node *n, struct hlist_head *h)
{
    struct hlist_node *first = h->first;
    n->next = first;
    if (first)
        first->pprev = &n->next;
    h->first = n;
    n->pprev = &h->first;
}
```



##### 1.1 binder_open总结

1. 创建binder_state结构体保存/dev/binder文件句柄fd、内存映射的起始地址和大小
2. 创建binder_procs链表，将保存Service_manager进程信息的binder_proc对应的binder_proc->proc_node加入binder_procs的list中（proc->proc_node是一个hlist_node链表）

#### 2.binder_become_context_manager(bs)

```c
frameworks\native\cmds\servicemanager\Binder.c：
int binder_become_context_manager(struct binder_state *bs)
{
    return ioctl(bs->fd, BINDER_SET_CONTEXT_MGR, 0);            //传入参数BINDER_SET_CONTEXT_MGR
}

static long binder_ioctl(struct file *filp, unsigned int cmd, unsigned long arg)        //cmd = BINDER_SET_CONTEXT_MGR
{
    int ret;
    struct binder_proc *proc = filp->private_data;      //获得binder_proc，binder_proc对应Service_manager进程 --- 从打开文件file的私有数据成员变量private_data中获取binder_proc
    struct binder_thread *thread;
    unsigned int size = _IOC_SIZE(cmd);
    void __user *ubuf = (void __user *)arg;
    ret = wait_event_interruptible(binder_user_error_wait, binder_stop_on_user_error < 2);
    if (ret)
        return ret;
    binder_lock(__func__);
    thread = binder_get_thread(proc);       //获得Service_manager线程的信息binder_thread
    if (thread == NULL) {
        ret = -ENOMEM;
        goto err;
    }
    switch (cmd) {
    ...
    case BINDER_SET_CONTEXT_MGR:
        if (binder_context_mgr_node != NULL) {      //由binder_context_mgr_node = binder_new_node(proc, NULL, NULL);可知：binder_context_mgr_node为ServiceManager对应的binder_node
            ...
        }
        ret = security_binder_set_context_mgr(proc->tsk);
        if (ret < 0)
            goto err;
        if (binder_context_mgr_uid != -1) {             //binder_context_mgr_uid表示ServiceManager进程的uid
            if (binder_context_mgr_uid != current->cred->euid) {
                ...
            }
        } else {
        binder_context_mgr_uid = current->cred->euid;
        binder_context_mgr_node = binder_new_node(proc, NULL, NULL);        //binder_context_mgr_node为ServiceManager对应的binder_node，且binder_node.proc对应Service_manager进程
        binder_context_mgr_node->local_weak_refs++;
        binder_context_mgr_node->local_strong_refs++;
        binder_context_mgr_node->has_strong_ref = 1;
        binder_context_mgr_node->has_weak_ref = 1;
        break;
    }
    ret = 0;
    ...
    return ret;
}
```

##### 2.1  binder_get_thread

```c
static struct binder_thread *binder_get_thread(struct binder_proc *proc)        //proc对应Service_manager进程
{
    struct binder_thread *thread = NULL;
    struct rb_node *parent = NULL;
    struct rb_node **p = &proc->threads.rb_node;
    /*尽量从threads树中查找和current线程匹配的binder_thread节点*/
    while (*p) {
        parent = *p;
        thread = rb_entry(parent, struct binder_thread, rb_node);
        if (current->pid < thread->pid)
            p = &(*p)->rb_left;
        else if (current->pid > thread->pid)
            p = &(*p)->rb_right;
        else
            break;
    }
    /*“找不到就创建”一个binder_thread节点*/
    if (*p == NULL) {       //第一次执行时，p为NULL，下一次执行时会进入while
        thread = kzalloc(sizeof(*thread), GFP_KERNEL);      //b. 创建Service_manager进程对应的binder_thread
        if (thread == NULL)
            return NULL;
        binder_stats_created(BINDER_STAT_THREAD);
        thread->proc = proc;                                                            //将Service_manager进程的binder_proc保存到binder_thread.proc
        thread->pid = current->pid;                                             //将Service_manager进程的PID保存到binder_thread.pid
        init_waitqueue_head(&thread->wait);
        INIT_LIST_HEAD(&thread->todo);
        rb_link_node(&thread->rb_node, parent, p);              //将binder_thread保存到红黑树中
        rb_insert_color(&thread->rb_node, &proc->threads);
        thread->looper |= BINDER_LOOPER_STATE_NEED_RETURN;
        thread->return_error = BR_OK;
        thread->return_error2 = BR_OK;
    }
    return thread;
}
```

此函数为获得proc对应进程下的所有线程中和当前线程pid相等的binder_thread



##### 2.2 binder_context_mgr_node = binder_new_node

```c
static struct binder_thread *binder_get_thread(struct binder_proc *proc)        //proc对应Service_manager进程
{
    struct binder_thread *thread = NULL;
    struct rb_node *parent = NULL;
    struct rb_node **p = &proc->threads.rb_node;
    /*尽量从threads树中查找和current线程匹配的binder_thread节点*/
    while (*p) {
        parent = *p;
        thread = rb_entry(parent, struct binder_thread, rb_node);
        if (current->pid < thread->pid)
            p = &(*p)->rb_left;
        else if (current->pid > thread->pid)
            p = &(*p)->rb_right;
        else
            break;
    }
    /*“找不到就创建”一个binder_thread节点*/
    if (*p == NULL) {       //第一次执行时，p为NULL，下一次执行时会进入while
        thread = kzalloc(sizeof(*thread), GFP_KERNEL);      //b. 创建Service_manager进程对应的binder_thread
        if (thread == NULL)
            return NULL;
        binder_stats_created(BINDER_STAT_THREAD);
        thread->proc = proc;                                                            //将Service_manager进程的binder_proc保存到binder_thread.proc
        thread->pid = current->pid;                                             //将Service_manager进程的PID保存到binder_thread.pid
        init_waitqueue_head(&thread->wait);
        INIT_LIST_HEAD(&thread->todo);
        rb_link_node(&thread->rb_node, parent, p);              //将binder_thread保存到红黑树中
        rb_insert_color(&thread->rb_node, &proc->threads);
        thread->looper |= BINDER_LOOPER_STATE_NEED_RETURN;
        thread->return_error = BR_OK;
        thread->return_error2 = BR_OK;
    }
    return thread;
}
```



##### 2.3 binder_become_context_manager总结

1. 创建ServiceManager线程的binder_thread，binder_thread.proc保存ServiceManager进程对应的binder_proc，binder_thread.pid保存当前进程ServiceManager的PID
2. 创建ServiceManager进程的binder_node，binder_node.proc保存binder_proc
3. 把ServiceManager进程对应的binder_proc保存到全局变量filp->private_data中



#### 3. binder_loop

```c
frameworks\native\cmds\servicemanager\Binder.c：
void binder_loop(struct binder_state *bs, binder_handler func)      //开启for循环，充当Server的角色，等待Client连接
{
    int res;
    struct binder_write_read bwr;
    uint32_t readbuf[32];
    bwr.write_size = 0;
    bwr.write_consumed = 0;
    bwr.write_buffer = 0;
    readbuf[0] = BC_ENTER_LOOPER;                                           //readbuf[0] = BC_ENTER_LOOPER
    binder_write(bs, readbuf, sizeof(uint32_t));
    for (;;) {
        bwr.read_size = sizeof(readbuf);
        bwr.read_consumed = 0;
        bwr.read_buffer = (uintptr_t) readbuf;      //bwr.read_buffer = BC_ENTER_LOOPER
        res = ioctl(bs->fd, BINDER_WRITE_READ, &bwr);       //bs->fd记录/dev/binder文件句柄，因此调用binder驱动的ioctl函数，传入参数BINDER_WRITE_READ，bwr.read_buffer = BC_ENTER_LOOPER，bwr.write_buffer = 0
        ...
        res = binder_parse(bs, 0, (uintptr_t) readbuf, bwr.read_consumed, func);
    }
}
```

##### 3.1 binder_write(bs, readbuf, sizeof(uint32_t));

```c
int binder_write(struct binder_state *bs, void *data, size_t len)
{
    struct binder_write_read bwr;
    int res;
    bwr.write_size = len;
    bwr.write_consumed = 0;
    bwr.write_buffer = (uintptr_t) data;        //bwr.write_buffer = data = BC_ENTER_LOOPER
    bwr.read_size = 0;
    bwr.read_consumed = 0;
    bwr.read_buffer = 0;
    res = ioctl(bs->fd, BINDER_WRITE_READ, &bwr);
    return res;
}

static long binder_ioctl(struct file *filp, unsigned int cmd, unsigned long arg)        //cmd = BINDER_WRITE_READ，bwr.read_size = 0，bwr.write_size = len
{
    int ret;
    struct binder_proc *proc = filp->private_data;      //获得Service_manager进程的binder_proc，从打开文件file的私有数据成员变量private_data中获取binder_proc
    struct binder_thread *thread;
    unsigned int size = _IOC_SIZE(cmd);
    void __user *ubuf = (void __user *)arg;
    ret = wait_event_interruptible(binder_user_error_wait, binder_stop_on_user_error < 2);
    if (ret)
        return ret;
    binder_lock(__func__);
    thread = binder_get_thread(proc);       //获得proc对应进程(Service_manager进程)下的所有线程中和当前线程pid相等的binder_thread
    if (thread == NULL) {
        ret = -ENOMEM;
        goto err;
    }
    switch (cmd) {
    ...
    case BINDER_WRITE_READ: {
        struct binder_write_read bwr;
        if (size != sizeof(struct binder_write_read)) {
            ret = -EINVAL;
            goto err;
        }
        if (copy_from_user(&bwr, ubuf, sizeof(bwr))) {      //把用户传递进来的参数转换成binder_write_read结构体，并保存在本地变量bwr中，bwr.write_buffer = BC_ENTER_LOOPER
            ret = -EFAULT;                                                                                                                                                                                                                          bwr.read_buffer  = 0
            goto err;
        }
        if (bwr.write_size > 0) {       //bwr.write_size = len
            ret = binder_thread_write(proc, thread, (void __user *)bwr.write_buffer, bwr.write_size, &bwr.write_consumed);      //bwr.write_buffer = BC_ENTER_LOOPER，bwr.write_consumed = 0
            if (ret < 0) {
                bwr.read_consumed = 0;
                if (copy_to_user(ubuf, &bwr, sizeof(bwr)))
                    ret = -EFAULT;
                goto err;
            }
        }
        if (bwr.read_size > 0) {        //bwr.read_size = 0
            ...
        }
        if (copy_to_user(ubuf, &bwr, sizeof(bwr))) {        //将bwr返回到用户空间
            ret = -EFAULT;
            goto err;
        }
        break;
    }
    ret = 0;
    ...
    return ret;
}

int binder_thread_write(struct binder_proc *proc, struct binder_thread *thread,         //参数binder_proc、binder_thread、binder_write_read
            void __user *buffer, int size, signed long *consumed)     //buffer = bwr.write_buffer = BC_ENTER_LOOPER
{
    uint32_t cmd;
    void __user *ptr = buffer + *consumed;
    void __user *end = buffer + size;
    while (ptr < end && thread->return_error == BR_OK) {
        if (get_user(cmd, (uint32_t __user *)ptr))                  //cmd = BC_ENTER_LOOPER
            return -EFAULT;
        ptr += sizeof(uint32_t);
        if (_IOC_NR(cmd) < ARRAY_SIZE(binder_stats.bc)) {
            binder_stats.bc[_IOC_NR(cmd)]++;
            proc->stats.bc[_IOC_NR(cmd)]++;
            thread->stats.bc[_IOC_NR(cmd)]++;
        }
        switch (cmd) {      //cmd = BC_ENTER_LOOPER
        case BC_ENTER_LOOPER:
            ...
            thread->looper |= BINDER_LOOPER_STATE_ENTERED;      //binder_thread.looper值变为BINDER_LOOPER_STATE_ENTERED，表明当前线程ServiceManager已经进入循环状态
            break;
    }
    return 0;
}
```

##### 3.2 res = ioctl(bs->fd, BINDER_WRITE_READ, &bwr);

```c
static long binder_ioctl(struct file *filp, unsigned int cmd, unsigned long arg)        //cmd = BINDER_WRITE_READ
{
    int ret;
    struct binder_proc *proc = filp->private_data;      //获得Service_manager进程的binder_proc，从打开文件file的私有数据成员变量private_data中获取binder_proc
    struct binder_thread *thread;
    unsigned int size = _IOC_SIZE(cmd);
    void __user *ubuf = (void __user *)arg;
    ret = wait_event_interruptible(binder_user_error_wait, binder_stop_on_user_error < 2);
    if (ret)
        return ret;
    binder_lock(__func__);
    thread = binder_get_thread(proc);       //获得proc对应进程(Service_manager进程)下的所有线程中和当前线程pid相等的binder_thread
    if (thread == NULL) {
        ret = -ENOMEM;
        goto err;
    }
    switch (cmd) {
    ...
    case BINDER_WRITE_READ: {
        struct binder_write_read bwr;
        if (size != sizeof(struct binder_write_read)) {
            ret = -EINVAL;
            goto err;
        }
        if (copy_from_user(&bwr, ubuf, sizeof(bwr))) {      //把用户传递进来的参数转换成binder_write_read结构体，并保存在本地变量bwr中，bwr.read_buffer  = BC_ENTER_LOOPER
            ret = -EFAULT;                                                                                                                                                                                                                          bwr.write_buffer = BC_ENTER_LOOPER
            goto err;
        }
        if (bwr.write_size > 0) {       //由binder_loop函数可知bwr.write_buffer = 0
            ret = binder_thread_write(proc, thread, (void __user *)bwr.write_buffer, bwr.write_size, &bwr.write_consumed);
            if (ret < 0) {
                bwr.read_consumed = 0;
                if (copy_to_user(ubuf, &bwr, sizeof(bwr)))
                    ret = -EFAULT;
                goto err;
            }
        }
        if (bwr.read_size > 0) {        //由binder_loop函数可知bwr.read_buffer = BC_ENTER_LOOPER
            /*读取binder_thread->todo的事物，并处理，执行完后bwr.read_buffer = BR_NOOP*/
            ret = binder_thread_read(proc, thread, (void __user *)bwr.read_buffer, bwr.read_size, &bwr.read_consumed, filp->f_flags & O_NONBLOCK);      //proc和thread分别发起传输动作的进程和线程
            if (!list_empty(&proc->todo))
                wake_up_interruptible(&proc->wait);
            if (ret < 0) {
                if (copy_to_user(ubuf, &bwr, sizeof(bwr)))
                    ret = -EFAULT;
                goto err;
            }
        }
        if (copy_to_user(ubuf, &bwr, sizeof(bwr))) {
            ret = -EFAULT;
            goto err;
        }
        break;
    }
    ret = 0;
    ...
    return ret;
}
```

###### 3.2.1 分析binder_thread_write

```c
int binder_thread_write(struct binder_proc *proc, struct binder_thread *thread,
            void __user *buffer, int size, signed long *consumed)
{
    ...
    return 0;
}
```

###### 3.2.2 分析binder_thread_read

```c
static int binder_thread_read(struct binder_proc *proc,
                  struct binder_thread *thread,
                  void  __user *buffer, int size,                       //buffer = bwr.read_buffer = BC_ENTER_LOOPER，consumed = 0
                  signed long *consumed, int non_block)
{
    void __user *ptr = buffer + *consumed;
    void __user *end = buffer + size;
    int ret = 0;
    int wait_for_proc_work;
    if (*consumed == 0) {
        if (put_user(BR_NOOP, (uint32_t __user *)ptr))      //把BR_NOOP写回到用户传进来的缓冲区ptr = *buffer + *consumed = bwr.read_buffer + bwr.read_consumed = bwr.read_buffer，即ptr = bwr.read_buffer = BR_NOOP
            return -EFAULT;
        ptr += sizeof(uint32_t);
    }
    ...
    while (1) {
        uint32_t cmd;
        struct binder_transaction_data tr;
        struct binder_work *w;
        struct binder_transaction *t = NULL;
        if (!list_empty(&thread->todo))
            w = list_first_entry(&thread->todo, struct binder_work, entry);         //从thread->todo队列中取出待处理的事项
        else if (!list_empty(&proc->todo) && wait_for_proc_work)
            w = list_first_entry(&proc->todo, struct binder_work, entry);
        else {
            if (ptr - buffer == 4 && !(thread->looper & BINDER_LOOPER_STATE_NEED_RETURN)) /* no data added */
                goto retry;
            break;
        }
        if (end - ptr < sizeof(tr) + 4)
            break;
        switch (w->type) {      //由待处理事项的type分类处理
            ...
        }
        if (t->buffer->target_node) {
            struct binder_node *target_node = t->buffer->target_node;
            tr.target.ptr = target_node->ptr;
            tr.cookie =  target_node->cookie;
            t->saved_priority = task_nice(current);
            if (t->priority < target_node->min_priority &&
                !(t->flags & TF_ONE_WAY))
                binder_set_nice(t->priority);
            else if (!(t->flags & TF_ONE_WAY) ||
                 t->saved_priority > target_node->min_priority)
                binder_set_nice(target_node->min_priority);
            cmd = BR_TRANSACTION;                                                                   //cmd = BR_TRANSACTION
        } else {
            ...
        }
        ...
        if (put_user(cmd, (uint32_t __user *)ptr))      //把cmd = BR_TRANSACTION写回到用户传进来的缓冲区ptr = bwr.read_buffer，故执行完binder_thread_read后cmd = bwr.read_buffer = BR_TRANSACTION
            return -EFAULT;
        ptr += sizeof(uint32_t);
        if (copy_to_user(ptr, &tr, sizeof(tr)))
            return -EFAULT;
        ptr += sizeof(tr);
    }
    return 0;
}
```



##### 3.3 binder_loop总结

1. 进入for (;;)死循环，执行binder_thread_write
2. 执行binder_thread_read，从binder_thread->todo队列中取出待处理的事项并处理，处理完thread->todo队列中待处理的事项后：cmd = bwr.read_buffer = BR_TRANSACTION



#### 4.ServiceManager启动总结：

**ServiceManager 的启动分为三步**

> 1. 打开Binder驱动，建立128K = 128*1024内存映射
> 2. 设置自己（ServiceManager）为Binder的大管家
> 3. 开启for循环，充当Server的角色，等待Client连接

- 在Binder驱动程序中为ServiceManager建立了三个结构体：binder_proc、binder_thread、binder_node
  binder_node.proc保存binder_proc，进程间通信的数据会发送到binder_proc的todo链表
  binder_proc进程里有很多线程，每个线程对应一个binder_thread，每个binder_thread用来处理一个Client的跨进程通信的请求



### ServiceManager 注册服务

以注册**WindowManagerService**为例
ServiceManager.addService(Context.WINDOW_SERVICE, wm); 

向ServiceManager注册WMS，wm为WindowManagerService，WindowManagerService继承
等价：ServiceManager.addService(“window”, new WindowManagerService(…));

```java
frameworks/base/core/java/android/os/ServiceManager.java：
public static void addService(String name, IBinder service) {
    try {
        getIServiceManager().addService(name, service, false);
    } catch (RemoteException e) {
        Log.e(TAG, "error in addService", e);
    }
}
```

#### 1. getIServiceManager()

```java
private static IServiceManager getIServiceManager() {
    if (sServiceManager != null) {
        return sServiceManager;
    }
    // Find the service manager
    sServiceManager = ServiceManagerNative.asInterface(BinderInternal.getContextObject());      //获得ServiceManager的代理
    return sServiceManager;
}
```

##### 1.1 BinderInternal.getContextObject()：

```java
frameworks/base/core/java/com/android/internal/os/BinderInternal.java:
public static final native IBinder getContextObject();

frameworks/base/core/jni/android_util_Binder.cpp：
{ "getContextObject", "()Landroid/os/IBinder;", (void*)android_os_BinderInternal_getContextObject },

static jobject android_os_BinderInternal_getContextObject(JNIEnv* env, jobject clazz)
{
    sp<IBinder> b = ProcessState::self()->getContextObject(NULL);       //返回new BpBinder(0);
    return javaObjectForIBinder(env, b);                //把这个BpBinder对象转换成一个BinderProxy对象
}
```

###### 1.1.1 sp b = ProcessState::self()->getContextObject(NULL)

```c++
sp<IBinder> ProcessState::getContextObject(const sp<IBinder>& /*caller*/)
{
    return getStrongProxyForHandle(0);
}

sp<IBinder> ProcessState::getStrongProxyForHandle(int32_t handle)       //handle = 0
{
    sp<IBinder> result;
    AutoMutex _l(mLock);
    handle_entry* e = lookupHandleLocked(handle);
    if (e != NULL) {
        IBinder* b = e->binder;
        if (b == NULL || !e->refs->attemptIncWeak(this)) {
            if (handle == 0) {
                Parcel data;
                status_t status = IPCThreadState::self()->transact(
                        0, IBinder::PING_TRANSACTION, data, NULL, 0);
                if (status == DEAD_OBJECT)
                   return NULL;
            }
            b = new BpBinder(handle);   //b = new BpBinder(0);，最终直接返回b
            e->binder = b;
            if (b) e->refs = b->getWeakRefs();
            result = b;
        } else {
            result.force_set(b);
            e->refs->decWeak(this);
        }
    }
    return result;
}
```

###### 1.1.2 return javaObjectForIBinder(env, b)

```c++
frameworks/base/core/jni/android_util_Binder.cpp：
jobject javaObjectForIBinder(JNIEnv* env, const sp<IBinder>& val)
{
    jobject object = env->NewObject(gBinderProxyOffsets.mClass, gBinderProxyOffsets.mConstructor);      //创建BinderProxy对象
    if (object != NULL) {
        env->SetLongField(object, gBinderProxyOffsets.mObject, (jlong)val.get());       //把BpBinder对象和BinderProxy对象关联起来；BinderProxy.mObject成员记录了new BpBinder(0)对象的地址
        val->incStrong((void*)javaObjectForIBinder);
                ...
        }
    return object;
}
```

**因此：BinderInternal.getContextObject()相当于new BinderProxy()，且BinderProxy.mObject成员记录了new BpBinder(0)对象的地址**



##### 1.2 ServiceManagerNative.asInterface(…)

```java
ServiceManagerNative.asInterface(new BinderProxy())
frameworks/base/core/java/android/os/ServiceManagerNative.java：
static public IServiceManager asInterface(IBinder obj)      //obj = new BinderProxy()，且BinderProxy.mObject成员记录了new BpBinder(0)对象的地址
{
    if (obj == null) {
        return null;
    }
    IServiceManager in = (IServiceManager)obj.queryLocalInterface(descriptor);
    if (in != null) {
        return in;
    }   
    return new ServiceManagerProxy(obj);        //返回ServiceManagerProxy，其中ServiceManagerProxy.mRemote = new BinderProxy()
}

class ServiceManagerProxy implements IServiceManager {
    public ServiceManagerProxy(IBinder remote) {
        mRemote = remote;
    }
}
```

###### 1.2.1 总结

分析getIServiceManager()可知，最终返回ServiceManagerProxy，其中ServiceManagerProxy.mRemote = new BinderProxy()，且BinderProxy.mObject成员记录了new BpBinder(0)对象的地址



#### 2. ServiceManagerProxy.addService(…)

因此：getIServiceManager().addService(name, service, false);
等价：ServiceManagerProxy.addService(“window”, new WindowManagerService(…), false);

```java
frameworks/base/core/java/android/os/ServiceManagerNative.java：
class ServiceManagerProxy implements IServiceManager {
    public void addService(String name, IBinder service, boolean allowIsolated)     //name = "window"，service = new WindowManagerService(...)
            throws RemoteException {
        Parcel data = Parcel.obtain();      //创建一个Parcel
        Parcel reply = Parcel.obtain();
        /*向Parcel中写入需要传输的数据*/
        data.writeInterfaceToken(IServiceManager.descriptor);
        data.writeString(name);                             //name = "window"，向Parcel中写入服务名"window"
        data.writeStrongBinder(service);            //service = new WindowManagerService(...)，向Parcel中写入服务的本地对象new WindowManagerService(...)
        data.writeInt(allowIsolated ? 1 : 0);
        mRemote.transact(ADD_SERVICE_TRANSACTION, data, reply, 0);      //mRemote = new BinderProxy()，且BinderProxy.mObject成员记录了new BpBinder(0)对象的地址
        reply.recycle();
        data.recycle();
    }
}
```



##### 2.1 Parcel.obtain();

```java
frameworks/base/core/java/android/os/Parcel.java：
public static Parcel obtain() {
    ...
    return new Parcel(0);
}
```



##### 2.2 data.writeString(“window”)

```c++
frameworks/base/core/java/android/os/Parcel.java：
public final void writeString(String val) {
    nativeWriteString(mNativePtr, val);
}
frameworks/base/core/jni/android_os_Parcel.cpp：
{"nativeWriteString",         "(JLjava/lang/String;)V", (void*)android_os_Parcel_writeString},
static void android_os_Parcel_writeString(JNIEnv* env, jclass clazz, jlong nativePtr, jstring val)
{
    Parcel* parcel = reinterpret_cast<Parcel*>(nativePtr);
    if (parcel != NULL) {
            ...
        err = parcel->writeString16(str, env->GetStringLength(val));
    }
}
frameworks/native/libs/binder/Parcel.cpp：
status_t Parcel::writeString16(const String16& str)
{
    return writeString16(str.string(), str.size());
}
status_t Parcel::writeString16(const char16_t* str, size_t len)
{
    status_t err = writeInt32(len);     //写入数据长度
    if (err == NO_ERROR) {
        len *= sizeof(char16_t);
        uint8_t* data = (uint8_t*)writeInplace(len+sizeof(char16_t));       //计算复制数据的目标地址 = mData + mDataPos
        if (data) {
            memcpy(data, str, len); //复制数据到目标地址
            *reinterpret_cast<char16_t*>(data+len) = 0;
            return NO_ERROR;
        }
        err = mError;
    }
    return err;
}
status_t Parcel::writeInt32(int32_t val)
{
    return writeAligned(val);
}
void* Parcel::writeInplace(size_t len)
{
        ...
    uint8_t* const data = mData+mDataPos;       //复制数据的目标地址 = mData+mDataPos
    return data;
}
static void memcpy(void* dst, void* src, size_t size) {
    char* dst_c = (char*) dst, *src_c = (char*) src;
    for (; size > 0; size--) {
        *dst_c++ = *src_c++;
    }
}
```

**分析data.writeString(“window”);可知：data.mData保存着”window”**



##### 2.3 data.writeStrongBinder(new WindowManagerService(…));

```c++
frameworks/base/core/java/android/os/Parcel.java：
public final void writeStrongBinder(IBinder val) {
    nativeWriteStrongBinder(mNativePtr, val);               //val = new WindowManagerService(...)
}
frameworks/base/core/jni/android_os_Parcel.cpp：
{"nativeWriteStrongBinder",   "(JLandroid/os/IBinder;)V", (void*)android_os_Parcel_writeStrongBinder},

static void android_os_Parcel_writeStrongBinder(JNIEnv* env, jclass clazz, jlong nativePtr, jobject object)
{
    Parcel* parcel = reinterpret_cast<Parcel*>(nativePtr);
    if (parcel != NULL) {
        const status_t err = parcel->writeStrongBinder(ibinderForJavaObject(env, object));      //object = new WindowManagerService(...)
        if (err != NO_ERROR) {
            signalExceptionForError(env, clazz, err);
        }
    }
}
frameworks/native/libs/binder/Parcel.cpp：
status_t Parcel::writeStrongBinder(const sp<IBinder>& val)
{
    return flatten_binder(ProcessState::self(), val, this);     //val = new WindowManagerService(...)
}
status_t flatten_binder(const sp<ProcessState>& /*proc*/,
    const sp<IBinder>& binder, Parcel* out)                                     //binder = new WindowManagerService(...)，out = data
{
    flat_binder_object obj;
    obj.flags = 0x7f | FLAT_BINDER_FLAG_ACCEPTS_FDS;
    if (binder != NULL) {
        IBinder *local = binder->localBinder();     //返回BBinder                 //localBinder和remoteBinder是虚函数，服务端BBinder实现了localBinder, 客户端BpBinder实现了remoteBinder
        if (!local) {
            BpBinder *proxy = binder->remoteBinder();       //返回BpBinder
            if (proxy == NULL) {
                ALOGE("null proxy");
            }
            const int32_t handle = proxy ? proxy->handle() : 0;
            ...
        } else {
                /*构造flat_binder_object*/
            obj.type = BINDER_TYPE_BINDER;      //flat_binder_object.type = BINDER_TYPE_BINDER
            obj.binder = reinterpret_cast<uintptr_t>(local->getWeakRefs());     //reinterpret_cast<uintptr_t>为类型的强制转换
            obj.cookie = reinterpret_cast<uintptr_t>(local);            //flat_binder_object.cookie = BBinder，其中BBinder对应着new WindowManagerService(...)的服务端
        }
    } else {
        ...
    }
    return finish_flatten_binder(binder, obj, out);
}
inline static status_t finish_flatten_binder(
    const sp<IBinder>& /*binder*/, const flat_binder_object& flat, Parcel* out)     //flat = flat_binder_object， out = Parcel
{
    return out->writeObject(flat, false);       //向Parcel中写入flat_binder_object，其中flat_binder_object.cookie保存着new WindowManagerService(...)的服务端
}
status_t Parcel::writeObject(const flat_binder_object& val, bool nullMetaData)  //val = flat_binder_object，其中flat_binder_object.cookie保存着new WindowManagerService(...)的服务端
{
    const bool enoughData = (mDataPos+sizeof(val)) <= mDataCapacity;
    const bool enoughObjects = mObjectsSize < mObjectsCapacity;
    if (enoughData && enoughObjects) {
        *reinterpret_cast<flat_binder_object*>(mData+mDataPos) = val;
        if (nullMetaData || val.binder != 0) {
            mObjects[mObjectsSize] = mDataPos;      //Parcel.mObjects保存new WindowManagerService(...)的服务端
            acquire_object(ProcessState::self(), val, this);
            mObjectsSize++;
        }
    }
        ...
}
```

**分析data.writeStrongBinder(new WindowManagerService(…));可知：data.mObjects保存new WindowManagerService(…)的服务端**



##### 2.4 mRemote.transact(ADD_SERVICE_TRANSACTION, data, reply, 0);

```c++
frameworks/base/core/java/android/os/Binder.java：
final class BinderProxy implements IBinder {
    public boolean transact(int code, Parcel data, Parcel reply, int flags) throws RemoteException {        //code = ADD_SERVICE_TRANSACTION，data = Parcel，data.mData保存着"window"，data.mObjects保存new WindowManagerService(...)的服务端
        Binder.checkParcel(this, code, data, "Unreasonably large binder buffer");
        return transactNative(code, data, reply, flags);
    }
    public native boolean transactNative(int code, Parcel data, Parcel reply,           //JNI
            int flags) throws RemoteException;
}

frameworks/base/core/jni/android_util_Binder.cpp：
{"transactNative",      "(ILandroid/os/Parcel;Landroid/os/Parcel;I)Z", (void*)android_os_BinderProxy_transact},

static jboolean android_os_BinderProxy_transact(JNIEnv* env, jobject obj,
        jint code, jobject dataObj, jobject replyObj, jint flags)                   //code = ADD_SERVICE_TRANSACTION，dataObj = Parcel，dataObj.mData保存着"window"，dataObj.mObjects保存new WindowManagerService(...)的服务端
{
        /*在2.1.1.2分析env->SetLongField(object, gBinderProxyOffsets.mObject, (jlong)val.get());可知BinderProxy.mObject成员记录了new BpBinder(0)对象的地址*/
        IBinder* target = (IBinder*)env->GetLongField(obj, gBinderProxyOffsets.mObject);        //通过此方法获得BpBinder --- ServiceManager客户端的内存地址
        status_t err = target->transact(code, *data, reply, flags);
}

frameworks/native/libs/binder/BpBinder.cpp：
status_t BpBinder::transact(
    uint32_t code, const Parcel& data, Parcel* reply, uint32_t flags)
{
    if (mAlive) {
        status_t status = IPCThreadState::self()->transact(
            mHandle, code, data, reply, flags);
        if (status == DEAD_OBJECT) mAlive = 0;
        return status;
    }
    return DEAD_OBJECT;
}

frameworks/native/libs/binder/IPCThreadState.cpp：
status_t IPCThreadState::transact(int32_t handle,
                                  uint32_t code, const Parcel& data,
                                  Parcel* reply, uint32_t flags)        //code = ADD_SERVICE_TRANSACTION，data = Parcel，data.mData保存着"window"，data.mObjects保存new WindowManagerService(...)的服务端
{
    status_t err = data.errorCheck();
    err = writeTransactionData(BC_TRANSACTION, flags, handle, code, data, NULL);            //打包数据成Binder驱动规定的格式
    err = waitForResponse(reply);
    return err;
}

status_t IPCThreadState::writeTransactionData(int32_t cmd, uint32_t binderFlags,
    int32_t handle, uint32_t code, const Parcel& data, status_t* statusBuffer)              //cmd = BC_TRANSACTION，code = ADD_SERVICE_TRANSACTION
{
    binder_transaction_data tr;     //由输入数据Parcel构造binder_transaction_data结构体
    tr.target.ptr = 0;
    tr.target.handle = handle;      //handle = BpBinder.mHandle对应着ServiceManager进程的handle，在注册服务时ServiceManager相当于Server
    tr.code = code;                             //binder_transaction_data.code = ADD_SERVICE_TRANSACTION
    tr.flags = binderFlags;
    tr.cookie = 0;
    tr.sender_pid = 0;
    tr.sender_euid = 0;
    tr.data_size = data.ipcDataSize();
    tr.data.ptr.buffer = data.ipcData();                //tr.data.ptr.buffer  = data.ipcData() = mData = "window"，更开始写入数据时mDataPos = 0，故mData + mDataPos = mData
    tr.offsets_size = data.ipcObjectsCount()*sizeof(binder_size_t);
    tr.data.ptr.offsets = data.ipcObjects();        //tr.data.ptr.offsets = data.ipcObjects() = mObjects = new WindowManagerService(...)的服务端
    mOut.writeInt32(cmd);                                               //向IPCThreadState.mOut中写入cmd = BC_TRANSACTION
    mOut.write(&tr, sizeof(tr));        //向IPCThreadState.mOut中写入tr = binder_transaction_data，其中binder_transaction_data.target.handle = BpBinder.mHandle对应着ServiceManager进程的handle，在注册服务时ServiceManager相当于Server
    return NO_ERROR;                                                                                                                                                             binder_transaction_data.data.ptr.buffer  = data.ipcData() = mData = "window"
}                                                                                                                                                                                                    binder_transaction_data.data.ptr.offsets = data.ipcObjects() = mObjects = new WindowManagerService(...)的服务端

status_t IPCThreadState::waitForResponse(Parcel *reply, status_t *acquireResult)
{
    int32_t cmd;
    int32_t err;
    while (1) {     //死循环等待，直到talkWithDriver返回NO_ERROR
        if ((err=talkWithDriver()) < NO_ERROR) break;           //把数据发送给binder驱动
        err = mIn.errorCheck();
        if (err < NO_ERROR) break;
        if (mIn.dataAvail() == 0) continue;
        cmd = mIn.readInt32();          //读取cmd = BC_TRANSACTION
        switch (cmd) {
        ...
        default:
            err = executeCommand(cmd);
        }
    }
}

status_t IPCThreadState::talkWithDriver(bool doReceive)
{
    binder_write_read bwr;
    const bool needRead = mIn.dataPosition() >= mIn.dataSize();         //needRead = true，doReceive = false
    const size_t outAvail = (!doReceive || needRead) ? mOut.dataSize() : 0;
    bwr.write_size = outAvail;
    bwr.write_buffer = (uintptr_t)mOut.data();      //binder_write_read.write_buffer = mOut，mOut保存binder_transaction_data，其中binder_transaction_data.target.handle = BpBinder.mHandle对应着ServiceManager进程的handle，在注册服务时ServiceManager相当于Server
    if (doReceive && needRead) {                                                                                                                                                                                                binder_transaction_data.data.ptr.buffer  = data.ipcData() = mData = "window"
        bwr.read_size = mIn.dataCapacity();                                                                                                                                                                         binder_transaction_data.data.ptr.offsets = data.ipcObjects() = mObjects = new WindowManagerService(...)的服务端
        bwr.read_buffer = (uintptr_t)mIn.data();
    } else {
        bwr.read_size = 0;
        bwr.read_buffer = 0;                                            //binder_write_read.read_buffer = 0
    }
    if ((bwr.write_size == 0) && (bwr.read_size == 0)) return NO_ERROR;
    bwr.write_consumed = 0;                                             //binder_write_read.write_consumed = 0
    bwr.read_consumed = 0;                                              //binder_write_read.read_consumed = 0
    status_t err;
    do {
        if (ioctl(mProcess->mDriverFD, BINDER_WRITE_READ, &bwr) >= 0)       //fd = mProcess->mDriverFD为/dev/binder文件句柄（表示调用Binder驱动的ioctl），binder_write_read.write_buffer保存binder_transaction_data
            err = NO_ERROR;
        else
            err = -errno;
        ...
    } while (err == -EINTR);
    if (err >= NO_ERROR) {
        if (bwr.write_consumed > 0) {
            if (bwr.write_consumed < mOut.dataSize())
                mOut.remove(0, bwr.write_consumed);     //清空之前写入Binder驱动的内容
            else
                mOut.setDataSize(0);
        }
        if (bwr.read_consumed > 0) {
            mIn.setDataSize(bwr.read_consumed);     //设置从Binder驱动读取的内容
            mIn.setDataPosition(0);
        }
        return NO_ERROR;
    }
    return err;
}

drivers/staging/android/binder.c
static long binder_ioctl(struct file *filp, unsigned int cmd, unsigned long arg)        //cmd = BINDER_WRITE_READ，arg = binder_write_read，其中binder_write_read.write_buffer = mOut，mOut保存binder_transaction_data，其中binder_transaction_data.target.handle = BpBinder.mHandle对应着ServiceManager进程的handle，在注册服务时ServiceManager相当于Server
{                                                                                                                                                                                                                                                                                       binder_transaction_data.data.ptr.buffer  = data.ipcData() = mData = "window"
    int ret;                                                                                                                                                                                                                                                                    binder_transaction_data.data.ptr.offsets = data.ipcObjects() = mObjects = new WindowManagerService(...)的服务端
    struct binder_proc *proc = filp->private_data;      //获得ServiceManager进程对应的binder_proc --- 从打开文件file的私有数据成员变量private_data中获取binder_proc
    struct binder_thread *thread;
    unsigned int size = _IOC_SIZE(cmd);
    void __user *ubuf = (void __user *)arg;
    ret = wait_event_interruptible(binder_user_error_wait, binder_stop_on_user_error < 2);
    if (ret)
        return ret;
    thread = binder_get_thread(proc);               //获得ServiceManager进程用于处理当前跨进程传输数据的线程binder_thread --- 此线程专门用于处理此跨进程间通信
    switch (cmd) {
    case BINDER_WRITE_READ: {
        struct binder_write_read bwr;
        if (size != sizeof(struct binder_write_read)) {
            ret = -EINVAL;
            goto err;
        }
        if (copy_from_user(&bwr, ubuf, sizeof(bwr))) {      //读取执行ioctl传进的参数ubuf = arg并保存到本地对象binder_write_read中
            ret = -EFAULT;
            goto err;
        }
        if (bwr.write_size > 0) {           //binder_write_read.write_buffer = mOut，mOut保存binder_transaction_data，其中binder_transaction_data.target.handle = BpBinder.mHandle对应着ServiceManager进程的handle，在注册服务时ServiceManager相当于Server
                                            //                                                                                                                                                      binder_transaction_data.data.ptr.buffer  = data.ipcData() = mData = "window"
                                            //                                                                                                                                                      binder_transaction_data.data.ptr.offsets = data.ipcObjects() = mObjects = new WindowManagerService(...)的服务端
            ret = binder_thread_write(proc, thread, (void __user *)bwr.write_buffer, bwr.write_size, &bwr.write_consumed);      //参数binder_proc、binder_thread、binder_write_read
            if (ret < 0) {
                bwr.read_consumed = 0;
                if (copy_to_user(ubuf, &bwr, sizeof(bwr)))
                    ret = -EFAULT;
                goto err;
            }
        }
        if (bwr.read_size > 0) {        //由函数talkWithDriver知：binder_write_read.read_size = 0即bwr.read_size = 0
            ret = binder_thread_read(proc, thread, (void __user *)bwr.Read_Buffer, bwr.read_size, &bwr.read_consumed, filp->f_flags & O_NONBLOCK);
            ...
        }
        if (copy_to_user(ubuf, &bwr, sizeof(bwr))) {        //将操作结果bwr返回到用户空间ubuf
            ret = -EFAULT;
            goto err;
        }
        break;
    }
    ...
    }
    ret = 0;
err:
    ...
    return ret;
}

//创建binder_node结构体，binder_node.cookie = new WindowManagerService(...)的服务端
int binder_thread_write(struct binder_proc *proc, struct binder_thread *thread,         //参数binder_proc、binder_thread、binder_write_read
            void __user *buffer, int size, signed long *consumed)                         //buffer = binder_write_read.write_buffer，binder_write_read.write_buffer = mOut，mOut保存binder_transaction_data
{
    uint32_t cmd;
    void __user *ptr = buffer + *consumed;                  //*ptr = *buffer + *consumed = bwr.write_buffer + bwr.write_consumed = bwr.write_buffer = mOut，mOut保存binder_transaction_data
                                                                                                    //binder_transaction_data.target.handle = BpBinder.mHandle对应着ServiceManager进程的handle，在注册服务时ServiceManager相当于Server
                                                                                                    //binder_transaction_data.data.ptr.buffer  = data.ipcData() = mData = "window"                                                    
                                                                                                    //binder_transaction_data.data.ptr.offsets = data.ipcObjects() = mObjects = new WindowManagerService(...)的服务端                 
    void __user *end = buffer + size;
    while (ptr < end && thread->return_error == BR_OK) {
        if (get_user(cmd, (uint32_t __user *)ptr))      //在IPCThreadState::writeTransactionData执行mOut.writeInt32(cmd);向IPCThreadState.mOut中写入cmd = BC_TRANSACTION，又*ptr = mOut可知获得用户输入命令cmd = BC_TRANSACTION
            return -EFAULT;
        ptr += sizeof(uint32_t);
        if (_IOC_NR(cmd) < ARRAY_SIZE(binder_stats.bc)) {
            binder_stats.bc[_IOC_NR(cmd)]++;
            proc->stats.bc[_IOC_NR(cmd)]++;
            thread->stats.bc[_IOC_NR(cmd)]++;
        }
        switch (cmd) {      //cmd = BC_TRANSACTION
        case BC_TRANSACTION:
        case BC_REPLY: {
            struct binder_transaction_data tr;
            if (copy_from_user(&tr, ptr, sizeof(tr)))       //读取用户空间ptr的数据，保存到tr
                return -EFAULT;
            ptr += sizeof(tr);
            binder_transaction(proc, thread, &tr, cmd);     //cmd = BC_TRANSACTION，tr保存bwr.write_buffer = mOut，mOut保存binder_transaction_data
            break;
        }
    }
    return 0;
}


static void binder_transaction(struct binder_proc *proc,
                   struct binder_thread *thread,
                   struct binder_transaction_data *tr, int reply)       //reply = BC_TRANSACTION，tr保存bwr.write_buffer = mOut，mOut保存binder_transaction_data
                                                                                                                            //binder_transaction_data.target.handle = BpBinder.mHandle对应着ServiceManager进程的handle，在注册服务时ServiceManager相当于Server
                                                                                                                            //binder_transaction_data.data.ptr.buffer  = data.ipcData() = mData = "window"                                                    
                                                                                                                            //binder_transaction_data.data.ptr.offsets = data.ipcObjects() = mObjects = new WindowManagerService(...)的服务端
{
    struct binder_transaction *t;       //binder_transaction结构体
    struct binder_work *tcomplete;
    size_t *offp, *off_end;
    size_t off_min;
    struct binder_proc *target_proc;                            //3个关键结构体binder_proc、binder_thread、binder_node
    struct binder_thread *target_thread = NULL;
    struct binder_node *target_node = NULL;
    struct list_head *target_list;                              //list_head
    wait_queue_head_t *target_wait;
    struct binder_transaction *in_reply_to = NULL;
    struct binder_transaction_log_entry *e;
    uint32_t return_error = BR_OK;
    struct binder_ref *ref;
    ref = binder_get_ref(proc, tr->target.handle);  //由handle = binder_transaction_data.target.handle = BpBinder.mHandle找到binder_ref，它是对服务ServiceManager的引用
    target_node = ref->node;                                                //由binder_ref.node找到服务ServiceManager的binder_node
    target_proc = target_node->proc;                                //服务ServiceManager的binder_node.proc找到目标进程ServiceManager的binder_proc
    if (!reply && !(tr->flags & TF_ONE_WAY))
        t->from = thread;
    else
        t->from = NULL;
    if (target_thread) {
        e->to_thread = target_thread->pid;
        target_list = &target_thread->todo;
        target_wait = &target_thread->wait;
    } else {
        target_list = &target_proc->todo;
        target_wait = &target_proc->wait;
    }
    t->sender_euid = proc->tsk->cred->euid;
    t->to_proc = target_proc;           //目标进程ServiceManager对应的binder_proc
    t->to_thread = target_thread;   //目标进程ServiceManager用于处理此次进程通信对应的binder_thread
    t->code = tr->code;
    t->flags = tr->flags;
    t->priority = task_nice(current);
    t->buffer = binder_alloc_buf(target_proc, tr->data_size, tr->offsets_size, !reply && (t->flags & TF_ONE_WAY));
    t->buffer->allow_user_free = 0;
    t->buffer->debug_id = t->debug_id;
    t->buffer->transaction = t;                             
    t->buffer->target_node = target_node;       //目标进程ServiceManager对应的binder_node
    if (target_node)
        binder_inc_node(target_node, 1, 0, NULL);
    offp = (size_t *)(t->buffer->data + ALIGN(tr->data_size, sizeof(void *)));
    if (copy_from_user(t->buffer->data, tr->data.ptr.buffer, tr->data_size)) {      //t->buffer->data = tr->data.ptr.buffer = "window"
        ...
    }

    /*tr保存binder_transaction_data，其中binder_transaction_data.data.ptr.offsets = data.ipcObjects() = mObjects = new WindowManagerService(...)的服务端*/
    if (copy_from_user(offp, tr->data.ptr.offsets, tr->offsets_size)) {                     //offp            = binder_transaction_data.data.ptr.offsets = new WindowManagerService(...)的服务端
        ...
    }

    off_end = (void *)offp + tr->offsets_size;
    for (; offp < off_end; offp++) {        //即遍历从保存flat_binder_object的起始地址到结束地址
        struct flat_binder_object *fp;
        fp = (struct flat_binder_object *)(t->buffer->data + *offp);
        off_min = *offp + sizeof(struct flat_binder_object);
        switch (fp->type) {
        case BINDER_TYPE_BINDER:        //由2.2.3中flatten_binder函数的obj.type = BINDER_TYPE_BINDER;知flat_binder_object.type = BINDER_TYPE_BINDER
                                                    //                                                       obj.binder = reinterpret_cast<uintptr_t>(local->getWeakRefs());
                                                    //                                                       obj.cookie = reinterpret_cast<uintptr_t>(local);   其中local对应着new WindowManagerService(...)的服务端
        case BINDER_TYPE_WEAK_BINDER: {
            struct binder_ref *ref;
            struct binder_node *node = binder_get_node(proc, fp->binder);
            if (node == NULL) {
                /*为每一个服务创建一个binder_node结构体，binder_node.cookie = new WindowManagerService(...)的服务端*/
                node = binder_new_node(proc, fp->binder, fp->cookie);       //proc对应目标进程ServiceManager的binder_proc，fp->cookie对应着new WindowManagerService(...)的服务端
                node->min_priority = fp->flags & FLAT_BINDER_FLAG_PRIORITY_MASK;
                node->accept_fds = !!(fp->flags & FLAT_BINDER_FLAG_ACCEPTS_FDS);
            }
            ...
        } break;
        ...
    }
    if (reply) {
        binder_pop_transaction(target_thread, in_reply_to);
    } else if (!(t->flags & TF_ONE_WAY)) {
        t->need_reply = 1;
        t->from_parent = thread->transaction_stack;
        thread->transaction_stack = t;                                  //把binder_transaction结构体t保存到thread->transaction_stack，表示ServiceManager线程还有任务未完成
    }
    t->work.type = BINDER_WORK_TRANSACTION;
    list_add_tail(&t->work.entry, target_list);                 //把binder_transaction结构体t保存到ServiceManager线程的thread->todo队列，事项类型为BINDER_WORK_TRANSACTION
    tcomplete->type = BINDER_WORK_TRANSACTION_COMPLETE;
    list_add_tail(&tcomplete->entry, &thread->todo);
    if (target_wait)
        wake_up_interruptible(target_wait);             //唤醒ServiceManager线程，ServiceManager线程执行waitForResponse时休眠，直到talkWithDriver返回NO_ERROR
    return;
}

//为每一个服务创建一个binder_node结构体，binder_node.cookie = new WindowManagerService(...)的服务端
static struct binder_node *binder_new_node(struct binder_proc *proc,        //proc = binder_proc，cookie = new WindowManagerService(...)的服务端
                       void __user *ptr,
                       void __user *cookie)
{
    struct rb_node **p = &proc->nodes.rb_node;
    struct rb_node *parent = NULL;
    struct binder_node *node;
    while (*p) {
        parent = *p;
        node = rb_entry(parent, struct binder_node, rb_node);
        if (ptr < node->ptr)
            p = &(*p)->rb_left;
        else if (ptr > node->ptr)
            p = &(*p)->rb_right;
        else
            return NULL;
    }
    /*分配binder_node结构体*/
    node = kzalloc(sizeof(*node), GFP_KERNEL);
    if (node == NULL)
        return NULL;
    binder_stats_created(BINDER_STAT_NODE);
    rb_link_node(&node->rb_node, parent, p);    //将new WindowManagerService(...)服务对应的binder_node保存到红黑树中
    rb_insert_color(&node->rb_node, &proc->nodes);
    node->debug_id = ++binder_last_id;
    node->proc = proc;                                              //binder_node.proc = ServiceManager进程的binder_proc
    node->ptr = ptr;
    node->cookie = cookie;                                      //binder_node.cookie = new WindowManagerService(...)的服务端
    node->work.type = BINDER_WORK_NODE;
    INIT_LIST_HEAD(&node->work.entry);
    INIT_LIST_HEAD(&node->async_todo);
    ...
    return node;
}
```



##### 2.5 Binder_Loop

ServiceManager线程的thread->todo队列保存着binder_transaction结构体t，t->buffer->data = tr->data.ptr.buffer = “window”

```c++
frameworks/native/cmds/servicemanager/Binder.c：
void Binder_Loop(struct binder_state *bs, binder_handler func)      //开启for循环，充当Server的角色，等待Client连接
{
    int res;
    struct binder_write_read bwr;
    uint32_t readbuf[32];
    bwr.write_size = 0;
    bwr.write_consumed = 0;
    bwr.write_buffer = 0;
    readbuf[0] = BC_ENTER_LOOPER;
    binder_write(bs, readbuf, sizeof(uint32_t));
    for (;;) {
        bwr.read_size = sizeof(readbuf);
        bwr.read_consumed = 0;
        bwr.read_buffer = (uintptr_t) readbuf;      //由talkWithDriver函数可知bwr.read_buffer保存BR_TRANSACTION
        res = ioctl(bs->fd, BINDER_WRITE_READ, &bwr);       //bs->fd记录/dev/binder文件句柄，因此调用binder驱动的ioctl函数，传入参数BINDER_WRITE_READ
        ...                                                                                         //执行完ioctl后bwr.read_buffer = BR_TRANSACTION
        res = binder_parse(bs, 0, (uintptr_t) readbuf, bwr.read_consumed, func);
    }
}

static long binder_ioctl(struct file *filp, unsigned int cmd, unsigned long arg)        //cmd = BINDER_WRITE_READ
{
    int ret;
    struct binder_proc *proc = filp->private_data;      //获得Service_manager进程的binder_proc，从打开文件file的私有数据成员变量private_data中获取binder_proc
    struct binder_thread *thread;
    unsigned int size = _IOC_SIZE(cmd);
    void __user *ubuf = (void __user *)arg;
    ret = wait_event_interruptible(binder_user_error_wait, binder_stop_on_user_error < 2);
    if (ret)
        return ret;
    binder_lock(__func__);
    thread = binder_get_thread(proc);       //获得proc对应进程(Service_manager进程)下的所有线程中和当前线程pid相等的binder_thread
    if (thread == NULL) {
        ret = -ENOMEM;
        goto err;
    }
    switch (cmd) {
    ...
    case BINDER_WRITE_READ: {
        struct binder_write_read bwr;
        if (size != sizeof(struct binder_write_read)) {
            ret = -EINVAL;
            goto err;
        }
        if (copy_from_user(&bwr, ubuf, sizeof(bwr))) {      //把用户传递进来的参数转换成binder_write_read结构体，并保存在本地变量bwr中，bwr.read_buffer  = BC_ENTER_LOOPER
            ret = -EFAULT;                                                                                                                                                                                                                          bwr.write_buffer = 0
            goto err;
        }
        if (bwr.write_size > 0) {       //开始为0
            ...
        }
        if (bwr.read_size > 0) {        //由binder_loop函数可知bwr.read_buffer = BC_ENTER_LOOPER
            /*读取binder_thread->todo的事物，并处理，执行完后bwr.read_buffer = BR_TRANSACTION*/
            ret = binder_thread_read(proc, thread, (void __user *)bwr.read_buffer, bwr.read_size, &bwr.read_consumed, filp->f_flags & O_NONBLOCK);      //proc和thread分别发起传输动作的进程和线程
            if (!list_empty(&proc->todo))
                wake_up_interruptible(&proc->wait);
            if (ret < 0) {
                if (copy_to_user(ubuf, &bwr, sizeof(bwr)))
                    ret = -EFAULT;
                goto err;
            }
        }
        if (copy_to_user(ubuf, &bwr, sizeof(bwr))) {        //将bwr返回到用户空间
            ret = -EFAULT;
            goto err;
        }
        break;
    }
    ret = 0;
    ...
    return ret;
}

static int binder_thread_read(struct binder_proc *proc,
                  struct binder_thread *thread,
                  void  __user *buffer, int size,                       //buffer = bwr.read_buffer = BC_ENTER_LOOPER，consumed = 0
                  signed long *consumed, int non_block)
{
    void __user *ptr = buffer + *consumed;
    void __user *end = buffer + size;
    int ret = 0;
    int wait_for_proc_work;
    if (*consumed == 0) {
        if (put_user(BR_NOOP, (uint32_t __user *)ptr))      //把BR_NOOP写回到用户传进来的缓冲区ptr = *buffer + *consumed = bwr.read_buffer + bwr.read_consumed = bwr.read_buffer，即ptr = bwr.read_buffer = BR_NOOP
            return -EFAULT;                                                                     即bwr.read_buffer = BR_NOOP
        ptr += sizeof(uint32_t);
    }
    ...
    while (1) {
        uint32_t cmd;
        struct binder_transaction_data tr;
        struct binder_work *w;
        struct binder_transaction *t = NULL;
        /*在分析2.2.4 mRemote.transact执行binder_transaction时，向ServiceManager进程的todo链表插入类型BINDER_WORK_TRANSACTION的事项*/
        if (!list_empty(&thread->todo))
            w = list_first_entry(&thread->todo, struct binder_work, entry);         //从thread->todo队列中取出待处理的事项，事项类型BINDER_WORK_TRANSACTION
        else if (!list_empty(&proc->todo) && wait_for_proc_work)
            w = list_first_entry(&proc->todo, struct binder_work, entry);
        else {
            if (ptr - buffer == 4 && !(thread->looper & BINDER_LOOPER_STATE_NEED_RETURN)) /* no data added */
                goto retry;
            break;
        }
        if (end - ptr < sizeof(tr) + 4)
            break;
        switch (w->type) {      //由待处理事项的type分类处理，w->type = BINDER_WORK_TRANSACTION
            ...
            case BINDER_WORK_TRANSACTION: {
                t = container_of(w, struct binder_transaction, work);
            } break;
        }
        if (t->buffer->target_node) {
            struct binder_node *target_node = t->buffer->target_node;
            tr.target.ptr = target_node->ptr;           //tr.target.ptr = "window"
            tr.cookie =  target_node->cookie;           //tr.cookie     = new WindowManagerService(...)
            t->saved_priority = task_nice(current);
            if (t->priority < target_node->min_priority &&
                !(t->flags & TF_ONE_WAY))
                binder_set_nice(t->priority);
            else if (!(t->flags & TF_ONE_WAY) ||
                 t->saved_priority > target_node->min_priority)
                binder_set_nice(target_node->min_priority);
            cmd = BR_TRANSACTION;                                                                   //cmd = BR_TRANSACTION
        } else {
            tr.target.ptr = NULL;
            tr.cookie = NULL;
            cmd = BR_REPLY;
        }
        ...
        if (put_user(cmd, (uint32_t __user *)ptr))      //把cmd = BR_TRANSACTION写回到用户传进来的缓冲区ptr = bwr.read_buffer，故执行完binder_thread_read后cmd = bwr.read_buffer = BR_TRANSACTION
            return -EFAULT;                                                             即bwr.read_buffer = BR_TRANSACTION
        ptr += sizeof(uint32_t);
        if (copy_to_user(ptr, &tr, sizeof(tr)))             
            return -EFAULT;
        ptr += sizeof(tr);
    }
    return 0;
}

int binder_parse(struct binder_state *bs, struct binder_io *bio,
                 uintptr_t ptr, size_t size, binder_handler func)
{
    int r = 1;
    uintptr_t end = ptr + (uintptr_t) size;
    while (ptr < end) {
        uint32_t cmd = *(uint32_t *) ptr;           //读取cmd = ptr = readbuf = bwr.read_buffer = BR_TRANSACTION
        ptr += sizeof(uint32_t);
        switch(cmd) {
        ...
        case BR_TRANSACTION: {
            struct binder_transaction_data *txn = (struct binder_transaction_data *) ptr;       //由ptr构造binder_transaction_data结构体txn
            if ((end - ptr) < sizeof(*txn)) {
                ALOGE("parse: txn too small!\n");
                return -1;
            }
            binder_dump_txn(txn);
            if (func) {                                     //func为binder_handler函数指针
                unsigned rdata[256/4];
                struct binder_io msg;
                struct binder_io reply;
                int res;
                bio_init(&reply, rdata, sizeof(rdata), 4);          //接收到数据之后，构造一个binder_io结构体reply
                bio_init_from_txn(&msg, txn);               //由txn构造一个binder_io结构体msg
                res = func(bs, txn, &msg, &reply);          //调用处理函数 --- 由binder_loop(bs, svcmgr_handler)第二个参数可知func是函数指针binder_handler,这个函数指针指向了svcmgr_handler函数
                                                                                                //其中txn.code = SVC_MGR_ADD_SERVICE，msg保存服务名"window"和new WindowManagerService(...)服务的handle
                binder_send_reply(bs, &reply, txn->data.ptr.buffer, res);       //如果res为0，表示注册成功，代码0写入binder_io结构体reply中
            }
            ptr += sizeof(*txn);
            break;
        }
    }
    return r;
}

frameworks/native/cmds/servicemanager/Service_manager.c：
int svcmgr_handler(struct binder_state *bs,
                   struct binder_transaction_data *txn,
                   struct binder_io *msg,
                   struct binder_io *reply)
{
    struct svcinfo *si;
    uint16_t *s;
    size_t len;
    uint32_t handle;
    uint32_t strict_policy;
    int allow_isolated;
    if (txn->target.handle != svcmgr_handle)        //txn->target为NULL，svcmgr_handle为NULL(void* (0))
        return -1;
    if (txn->code == PING_TRANSACTION)
        return 0;
    strict_policy = bio_get_uint32(msg);
    s = bio_get_string16(msg, &len);            //返回bio->data
    if (s == NULL) {
        return -1;
    }
    if ((len != (sizeof(svcmgr_id) / 2)) ||
        memcmp(svcmgr_id, s, sizeof(svcmgr_id))) {
        fprintf(stderr,"invalid id %s\n", str8(s, len));
        return -1;
    }
    if (sehandle && selinux_status_updated() > 0) {
        struct selabel_handle *tmp_sehandle = selinux_android_service_context_handle();
        if (tmp_sehandle) {
            selabel_close(sehandle);
            sehandle = tmp_sehandle;
        }
    }
    switch(txn->code) {
    ...
    case SVC_MGR_ADD_SERVICE:
        s = bio_get_string16(msg, &len);        //由msg获得s = "window"
        if (s == NULL) {
            return -1;
        }
        handle = bio_get_ref(msg);                  //由msg获得new WindowManagerService(...)服务的handle
        allow_isolated = bio_get_uint32(msg) ? 1 : 0;
        if (do_add_service(bs, s, len, handle, txn->sender_euid,        //执行do_add_service
            allow_isolated, txn->sender_pid))
            return -1;
        break;
    }
    bio_put_uint32(reply, 0);       //将注册成功代码0写入binder_io结构体reply中
    return 0;
}

int do_add_service(struct binder_state *bs,
                   const uint16_t *s, size_t len,
                   uint32_t handle, uid_t uid, int allow_isolated,
                   pid_t spid)
{
    struct svcinfo *si;
    if (!handle || (len == 0) || (len > 127))
        return -1;
    if (!svc_can_register(s, len, spid)) {      //检查用户ID为uid的进程是否有权限请求Service Manager注册一个名称为s的Service组件
        return -1;
    }
    si = find_svc(s, len);      //来检查服务名称s是否被已经注册了的Service组件使用了
    if (si) {
        if (si->handle) {
            svcinfo_death(bs, si);
        }
        si->handle = handle;
    } else {
        si = malloc(sizeof(*si) + (len + 1) * sizeof(uint16_t));        //分配svn_info结构体内存
        if (!si) {
            return -1;
        }
        si->handle = handle;            //重要：si->handle对应new WindowManagerService(...)的服务端
        si->len = len;
        memcpy(si->name, s, (len + 1) * sizeof(uint16_t));          //重要：si->name = "window"，s表示要注册的Service组件的名称"window"
        si->name[len] = '\0';
        si->death.func = (void*) svcinfo_death;     //死亡通知
        si->death.ptr = si;
        si->allow_isolated = allow_isolated;
        si->next = svclist;         //si->next = svclist;和svclist = si;形成链表，将创建的svcinfo结构体放入链表，注意是从右向左放，即先创建的svcinfo在链表最右边
        svclist = si;
    }
    binder_acquire(bs, handle);         //增加相对应的Binder引用对象的引用计数值，避免它过早地被销毁
    binder_link_to_death(bs, handle, &si->death);               //向Binder驱动程序注册一个Binder本地对象死亡接受通知
    return 0;
}

struct svcinfo
{
    struct svcinfo *next;       //用于形成链表
    uint32_t handle;
    struct binder_death death;
    int allow_isolated;
    size_t len;
    uint16_t name[0];       //用于保存注册的Service组件的名称
};
```



#### 3. ServiceManager注册服务总结

**ServiceManager 注册服务过程**
例如ServiceManager.addService(“window”, new WindowManagerService(…));

1. 创建一个binder_node结构体，binder_node.cookie = new WindowManagerService(…)的服务端
2.  向ServiceManager的todo队列里面添加一条注册服务”window”的事务
3.  创建一个svcinfo结构体放入链表，且svcinfo.handle对应new WindowManagerService(…)的服务端，svcinfo.name保存服务的名称”window”

   

### ServiceManager获取服务

frameworks/base/services/core/java/com/android/server/InputMethodManagerService.java：
ServiceManager.getService(Context.WINDOW_SERVICE);
等价：ServiceManager.getService(“window”);



```java
frameworks/base/core/java/android/os/ServiceManager.java：
public static IBinder getService(String name) {
    try {
        IBinder service = sCache.get(name);
        if (service != null) {
            return service;
        } else {
            return getIServiceManager().getService(name);
        }
    } catch (RemoteException e) {
        Log.e(TAG, "error in getService", e);
    }
    return null;
}
```

getIServiceManager().getService(name)
等价：ServiceManagerProxy.getService(“window”) //ServiceManagerProxy.mRemote = new BinderProxy()

```java
//frameworks/base/core/java/android/os/ServiceManagerNative.java：
class ServiceManagerProxy implements IServiceManager {
    public IBinder getService(String name) throws RemoteException {
        Parcel data = Parcel.obtain();  //创建一个Parcel对象
        Parcel reply = Parcel.obtain();
        data.writeInterfaceToken(IServiceManager.descriptor);
        data.writeString(name);         //向Parcel中写入需要向ServiceManager查询的服务名称"window"
        mRemote.transact(GET_SERVICE_TRANSACTION, data, reply, 0);
        IBinder binder = reply.readStrongBinder();
        reply.recycle();
        data.recycle();
        return binder;
    }
}
```

1. Parcel.obtain(); //1. 创建一个Parcel对象
2. data.writeString(“window”); //2. 向Parcel中写入需要跨进程传输的数据
3. mRemote.transact(GET_SERVICE_TRANSACTION, data, reply, 0); //传入参数data（保存Proxy向native发送的数据），reply（保存native向Proxy返回的数据）



#### 1. mRemote.transact(GET_SERVICE_TRANSACTION, data, reply, 0);

由前面的分析可知：mRemote = new BinderProxy()
最终会调用：

```c
frameworks/native/libs/binder/IPCThreadState.cpp：
status_t IPCThreadState::transact(int32_t handle,
                                  uint32_t code, const Parcel& data,
                                  Parcel* reply, uint32_t flags)        //code = GET_SERVICE_TRANSACTION
{
    status_t err = data.errorCheck();
    err = writeTransactionData(BC_TRANSACTION, flags, handle, code, data, NULL);            //打包数据成Binder驱动规定的格式，code = GET_SERVICE_TRANSACTION，data的地址mData保存"window"
    err = waitForResponse(reply);
    return err;
}

status_t IPCThreadState::writeTransactionData(int32_t cmd, uint32_t binderFlags,
    int32_t handle, uint32_t code, const Parcel& data, status_t* statusBuffer)              //cmd = BC_TRANSACTION，code = GET_SERVICE_TRANSACTION，data的地址mData保存"window"
{
    binder_transaction_data tr;     //由输入数据Parcel构造binder_transaction_data结构体
    tr.target.ptr = 0;
    tr.target.handle = handle;      //binder_transaction_data.target.handle = BpBinder.mHandle
    tr.code = code;                             //binder_transaction_data.code = GET_SERVICE_TRANSACTION
    tr.flags = binderFlags;
    tr.cookie = 0;
    tr.sender_pid = 0;
    tr.sender_euid = 0;
    tr.data_size = data.ipcDataSize();
    tr.data.ptr.buffer = data.ipcData();        //tr.data.ptr.buffer = data.ipcData() = mData = "window"，写入数据到Parcel时mDataPos = 0，故Parcel数据的起始地址为mData
    tr.offsets_size = data.ipcObjectsCount()*sizeof(binder_size_t);
    tr.data.ptr.offsets = data.ipcObjects();
    mOut.writeInt32(cmd);       //向IPCThreadState.mOut中写入cmd = BC_TRANSACTION
    mOut.write(&tr, sizeof(tr));        //向IPCThreadState.mOut中写入tr = binder_transaction_data，其中binder_transaction_data.code = GET_SERVICE_TRANSACTION，binder_transaction_data.data.ptr.buffer = "window"
    return NO_ERROR;
}

status_t IPCThreadState::waitForResponse(Parcel *reply, status_t *acquireResult)
{
    int32_t cmd;
    int32_t err;
    while (1) {     //死循环等待，直到talkWithDriver返回NO_ERROR
        if ((err=talkWithDriver()) < NO_ERROR) break;           //把数据发送给binder驱动
        err = mIn.errorCheck();
        if (err < NO_ERROR) break;
        if (mIn.dataAvail() == 0) continue;
        cmd = mIn.readInt32();          //读取cmd = BC_TRANSACTION
        switch (cmd) {
        ...
        default:        //cmd == BC_TRANSACTION时会执行default
            err = executeCommand(cmd);
        }
    }
}

status_t IPCThreadState::talkWithDriver(bool doReceive)
{
    binder_write_read bwr;
    const bool needRead = mIn.dataPosition() >= mIn.dataSize();         //needRead = true，doReceive = false
    const size_t outAvail = (!doReceive || needRead) ? mOut.dataSize() : 0;
    bwr.write_size = outAvail;
    bwr.write_buffer = (uintptr_t)mOut.data();      //binder_write_read.write_buffer = mOut，mOut保存binder_transaction_data，其中binder_transaction_data.code = GET_SERVICE_TRANSACTION，binder_transaction_data.data.ptr.buffer = "window"
    if (doReceive && needRead) {
        bwr.read_size = mIn.dataCapacity();
        bwr.read_buffer = (uintptr_t)mIn.data();
    } else {
        bwr.read_size = 0;
        bwr.read_buffer = 0;                                            //binder_write_read.read_buffer = 0
    }
    if ((bwr.write_size == 0) && (bwr.read_size == 0)) return NO_ERROR;
    bwr.write_consumed = 0;                                             //binder_write_read.write_consumed = 0
    bwr.read_consumed = 0;                                              //binder_write_read.read_consumed = 0
    status_t err;
    do {
        if (ioctl(mProcess->mDriverFD, BINDER_WRITE_READ, &bwr) >= 0)       //fd = mProcess->mDriverFD为/dev/binder文件句柄（表示调用Binder驱动的ioctl），binder_write_read.write_buffer保存binder_transaction_data，其中binder_transaction_data.code = GET_SERVICE_TRANSACTION，binder_transaction_data.data.ptr.buffer = "window"
            err = NO_ERROR;
        else
            err = -errno;
        ...
    } while (err == -EINTR);
    ...
    return err;
}

drivers/staging/android/binder.c
static long binder_ioctl(struct file *filp, unsigned int cmd, unsigned long arg)        //cmd = BINDER_WRITE_READ，arg = binder_write_read，binder_write_read.write_buffer保存binder_transaction_data，其中binder_transaction_data.code = GET_SERVICE_TRANSACTION
{
    int ret;
    struct binder_proc *proc = filp->private_data;      //获得binder_proc --- 从打开文件file的私有数据成员变量private_data中获取binder_proc
    struct binder_thread *thread;
    unsigned int size = _IOC_SIZE(cmd);
    void __user *ubuf = (void __user *)arg;
    ret = wait_event_interruptible(binder_user_error_wait, binder_stop_on_user_error < 2);
    if (ret)
        return ret;
    thread = binder_get_thread(proc);           //获得当前线程的信息binder_thread --- binder_proc所在的线程（即ServiceManager所在线程）信息
    switch (cmd) {
    case BINDER_WRITE_READ: {
        struct binder_write_read bwr;
        if (size != sizeof(struct binder_write_read)) {
            ret = -EINVAL;
            goto err;
        }
        if (copy_from_user(&bwr, ubuf, sizeof(bwr))) {      //读取执行ioctl传进的参数ubuf = arg并保存到本地对象binder_write_read中
            ret = -EFAULT;
            goto err;
        }
        if (bwr.write_size > 0) {           //binder_write_read.write_buffer = mOut，mOut保存binder_transaction_data，其中binder_transaction_data.code = GET_SERVICE_TRANSACTION，binder_transaction_data.data.ptr.buffer = "window"
            ret = binder_thread_write(proc, thread, (void __user *)bwr.write_buffer, bwr.write_size, &bwr.write_consumed);      //参数binder_proc、binder_thread、binder_write_read
            if (ret < 0) {
                bwr.read_consumed = 0;
                if (copy_to_user(ubuf, &bwr, sizeof(bwr)))
                    ret = -EFAULT;
                goto err;
            }
        }
        if (bwr.read_size > 0) {        //bwr.read_size = 0
            ret = binder_thread_read(proc, thread, (void __user *)bwr.Read_Buffer, bwr.read_size, &bwr.read_consumed, filp->f_flags & O_NONBLOCK);
            ...
        }
        if (copy_to_user(ubuf, &bwr, sizeof(bwr))) {        //将操作结果bwr返回到用户空间ubuf
            ret = -EFAULT;
            goto err;
        }
        break;
    }
    ...
    }
    ret = 0;
err:
    ...
    return ret;
}

//创建binder_node结构体，binder_node.cookie = new WindowManagerService(...)的服务端
int binder_thread_write(struct binder_proc *proc, struct binder_thread *thread,         //参数binder_proc、binder_thread、binder_write_read
            void __user *buffer, int size, signed long *consumed)     //buffer = binder_write_read.write_buffer，binder_write_read.write_buffer = mOut，mOut保存binder_transaction_data，其中binder_transaction_data.code = GET_SERVICE_TRANSACTION，binder_transaction_data.data.ptr.buffer = "window"
{
    uint32_t cmd;
    void __user *ptr = buffer + *consumed;
    void __user *end = buffer + size;
    while (ptr < end && thread->return_error == BR_OK) {
        if (get_user(cmd, (uint32_t __user *)ptr))      //在IPCThreadState::writeTransactionData执行mOut.writeInt32(cmd);向IPCThreadState.mOut中写入cmd = BC_TRANSACTION，可知获得用户输入命令cmd = BC_TRANSACTION
                                                                                                    //*ptr = *buffer + *consumed = bwr.write_buffer + bwr.write_consumed = bwr.write_buffer = mOut，mOut保存binder_transaction_data，其中binder_transaction_data.code = GET_SERVICE_TRANSACTION，binder_transaction_data.data.ptr.buffer = "window"
            return -EFAULT;
        ptr += sizeof(uint32_t);
        if (_IOC_NR(cmd) < ARRAY_SIZE(binder_stats.bc)) {
            binder_stats.bc[_IOC_NR(cmd)]++;
            proc->stats.bc[_IOC_NR(cmd)]++;
            thread->stats.bc[_IOC_NR(cmd)]++;
        }
        switch (cmd) {      //cmd = BC_TRANSACTION
        case BC_TRANSACTION:
        case BC_REPLY: {
            struct binder_transaction_data tr;
            if (copy_from_user(&tr, ptr, sizeof(tr)))       //读取用户空间ptr的数据，保存到tr
                return -EFAULT;
            ptr += sizeof(tr);
            binder_transaction(proc, thread, &tr, cmd);     //cmd = BC_TRANSACTION，tr保存bwr.write_buffer = mOut，mOut保存binder_transaction_data，其中binder_transaction_data.code = GET_SERVICE_TRANSACTION，binder_transaction_data.data.ptr.buffer = "window"
            break;
        }
    }
    return 0;
}

static void binder_transaction(struct binder_proc *proc,
                   struct binder_thread *thread,
                   struct binder_transaction_data *tr, int reply)       //reply = BC_TRANSACTION，tr保存bwr.write_buffer = mOut，mOut保存binder_transaction_data，其中binder_transaction_data.code = GET_SERVICE_TRANSACTION，binder_transaction_data.data.ptr.buffer = "window"
{
    struct binder_transaction *t;       //binder_transaction结构体
    struct binder_work *tcomplete;
    size_t *offp, *off_end;
    size_t off_min;
    struct binder_proc *target_proc;                            //3个关键结构体binder_proc、binder_thread、binder_node
    struct binder_thread *target_thread = NULL;
    struct binder_node *target_node = NULL;
    struct list_head *target_list;                              //list_head
    wait_queue_head_t *target_wait;
    struct binder_transaction *in_reply_to = NULL;
    struct binder_transaction_log_entry *e;
    uint32_t return_error = BR_OK;
    struct binder_ref *ref;
    ref = binder_get_ref(proc, tr->target.handle);
    target_node = ref->node;                                                //binder_node = binder_ref.node
    target_proc = target_node->proc;                                //binder_proc = binder_node.proc，创建binder_node保存到binder_proc中
    if (!reply && !(tr->flags & TF_ONE_WAY))
        t->from = thread;
    else
        t->from = NULL;
    /*由binder_transaction_data结构体tr构造binder_transaction结构体t*/
    t->sender_euid = proc->tsk->cred->euid;
    t->to_proc = target_proc;
    t->to_thread = target_thread;
    t->code = tr->code;                     //重点：binder_transaction.code = binder_transaction_data.code = GET_SERVICE_TRANSACTION
    t->flags = tr->flags;
    t->priority = task_nice(current);
    t->buffer = binder_alloc_buf(target_proc, tr->data_size, tr->offsets_size, !reply && (t->flags & TF_ONE_WAY));
    t->buffer->allow_user_free = 0;
    t->buffer->debug_id = t->debug_id;
    t->buffer->transaction = t;                             
    t->buffer->target_node = target_node;
    if (target_node)
        binder_inc_node(target_node, 1, 0, NULL);
    offp = (size_t *)(t->buffer->data + ALIGN(tr->data_size, sizeof(void *)));
    if (copy_from_user(t->buffer->data, tr->data.ptr.buffer, tr->data_size)) {      //重点：binder_transaction.buffer.data = binder_transaction_data.data.ptr.buffer = "window"
        ...
    }
    if (copy_from_user(offp, tr->data.ptr.offsets, tr->offsets_size)) {     //offp = tr->data.ptr.offsets = NULL，因为在执行getService时未写入Object
        ...
    }
    off_end = (void *)offp + tr->offsets_size;
    for (; offp < off_end; offp++) {        //offp为空故不进入for循环
        ...
    }
    if (reply) {
        binder_pop_transaction(target_thread, in_reply_to);
    } else if (!(t->flags & TF_ONE_WAY)) {
        t->need_reply = 1;
        t->from_parent = thread->transaction_stack;
        thread->transaction_stack = t;                                  //把binder_transaction结构体t保存到thread->transaction_stack，表示ServiceManager线程还有任务未完成
    }
    t->work.type = BINDER_WORK_TRANSACTION;     //重点：binder_transaction->work.type = BINDER_WORK_TRANSACTION
    list_add_tail(&t->work.entry, target_list);     //重点：将binder_transaction放入ServiceManager进程的todo链表中，其中binder_transaction.code = binder_transaction_data.code = GET_SERVICE_TRANSACTION
    tcomplete->type = BINDER_WORK_TRANSACTION_COMPLETE;                                                                                                                             binder_transaction.buffer.data = binder_transaction_data.data.ptr.buffer = "window"
    list_add_tail(&tcomplete->entry, &thread->todo);
    if (target_wait)
        wake_up_interruptible(target_wait);     //唤醒ServiceManager线程，ServiceManager线程执行waitForResponse，直到talkWithDriver返回NO_ERROR
    return;
}
```



##### 1.1 总结

分析mRemote.transact(GET_SERVICE_TRANSACTION, data, reply, 0);可知
在ServiceManager进程的todo链表中保存着一个binder_transaction结构体，其中
binder_transaction.code = binder_transaction_data.code = GET_SERVICE_TRANSACTION
binder_transaction.buffer.data = binder_transaction_data.data.ptr.buffer = “window”



#### 2. Binder_Loop

ServiceManager线程的thread->todo队列保存着binder_transaction结构体t，t->buffer->data = tr->data.ptr.buffer = “window”

```c
frameworks/native/cmds/servicemanager/Binder.c：
void Binder_Loop(struct binder_state *bs, binder_handler func)      //开启for循环，充当Server的角色，等待Client连接
{
    int res;
    struct binder_write_read bwr;
    uint32_t readbuf[32];
    bwr.write_size = 0;
    bwr.write_consumed = 0;
    bwr.write_buffer = 0;
    readbuf[0] = BC_ENTER_LOOPER;
    binder_write(bs, readbuf, sizeof(uint32_t));
    for (;;) {
        bwr.read_size = sizeof(readbuf);
        bwr.read_consumed = 0;
        bwr.read_buffer = (uintptr_t) readbuf;
        res = ioctl(bs->fd, BINDER_WRITE_READ, &bwr);       //bs->fd记录/dev/binder文件句柄，因此调用binder驱动的ioctl函数，传入参数BINDER_WRITE_READ
        ...
        res = binder_parse(bs, 0, (uintptr_t) readbuf, bwr.read_consumed, func);
    }
}
```

##### 2.1 res = ioctl(bs->fd, BINDER_WRITE_READ, &bwr);

```c
static long binder_ioctl(struct file *filp, unsigned int cmd, unsigned long arg)        //cmd = BINDER_WRITE_READ
{
    int ret;
    struct binder_proc *proc = filp->private_data;      //获得Service_manager进程的binder_proc，从打开文件file的私有数据成员变量private_data中获取binder_proc
    struct binder_thread *thread;
    unsigned int size = _IOC_SIZE(cmd);
    void __user *ubuf = (void __user *)arg;
    ret = wait_event_interruptible(binder_user_error_wait, binder_stop_on_user_error < 2);
    if (ret)
        return ret;
    binder_lock(__func__);
    thread = binder_get_thread(proc);       //获得proc对应进程(Service_manager进程)下的所有线程中和当前线程pid相等的binder_thread
    if (thread == NULL) {
        ret = -ENOMEM;
        goto err;
    }
    switch (cmd) {
    ...
    case BINDER_WRITE_READ: {
        struct binder_write_read bwr;
        if (size != sizeof(struct binder_write_read)) {
            ret = -EINVAL;
            goto err;
        }
        if (copy_from_user(&bwr, ubuf, sizeof(bwr))) {      //把用户传递进来的参数转换成binder_write_read结构体，并保存在本地变量bwr中，bwr.read_buffer  = BC_ENTER_LOOPER
            ret = -EFAULT;                                                                                                                                                                                                                          bwr.write_buffer = 0
            goto err;
        }
        if (bwr.write_size > 0) {       //开始为0
            ...
        }
        if (bwr.read_size > 0) {        //由binder_loop函数可知bwr.read_buffer = BC_ENTER_LOOPER
            /*读取binder_thread->todo的事物，并处理，执行完后bwr.read_buffer = BR_TRANSACTION*/
            ret = binder_thread_read(proc, thread, (void __user *)bwr.read_buffer, bwr.read_size, &bwr.read_consumed, filp->f_flags & O_NONBLOCK);      //proc和thread分别发起传输动作的进程和线程
            if (!list_empty(&proc->todo))
                wake_up_interruptible(&proc->wait);
            if (ret < 0) {
                if (copy_to_user(ubuf, &bwr, sizeof(bwr)))
                    ret = -EFAULT;
                goto err;
            }
        }
        if (copy_to_user(ubuf, &bwr, sizeof(bwr))) {        //将bwr返回到用户空间
            ret = -EFAULT;
            goto err;
        }
        break;
    }
    ret = 0;
    ...
    return ret;
}

static int binder_thread_read(struct binder_proc *proc,
                  struct binder_thread *thread,
                  void  __user *buffer, int size,                       //buffer = bwr.read_buffer = BC_ENTER_LOOPER，consumed = 0
                  signed long *consumed, int non_block)
{
    void __user *ptr = buffer + *consumed;
    void __user *end = buffer + size;
    int ret = 0;
    int wait_for_proc_work;
    if (*consumed == 0) {
        if (put_user(BR_NOOP, (uint32_t __user *)ptr))      //把BR_NOOP写回到用户传进来的缓冲区ptr = *buffer + *consumed = bwr.read_buffer + bwr.read_consumed = bwr.read_buffer，即ptr = bwr.read_buffer = BR_NOOP
            return -EFAULT;                                                                     即bwr.read_buffer = BR_NOOP
        ptr += sizeof(uint32_t);
    }
    ...
    while (1) {
        uint32_t cmd;
        struct binder_transaction_data tr;
        struct binder_work *w;
        struct binder_transaction *t = NULL;
        /*在3.1 分析mRemote.transact执行binder_transaction时，向ServiceManager进程的todo链表插入类型BINDER_WORK_TRANSACTION的事项*/
        if (!list_empty(&thread->todo))
            w = list_first_entry(&thread->todo, struct binder_work, entry);         //从thread->todo队列中取出待处理的事项，事项类型BINDER_WORK_TRANSACTION
        else if (!list_empty(&proc->todo) && wait_for_proc_work)
            w = list_first_entry(&proc->todo, struct binder_work, entry);
        else {
            if (ptr - buffer == 4 && !(thread->looper & BINDER_LOOPER_STATE_NEED_RETURN)) /* no data added */
                goto retry;
            break;
        }
        if (end - ptr < sizeof(tr) + 4)
            break;
        switch (w->type) {      //由待处理事项的type分类处理，w->type = BINDER_WORK_TRANSACTION
            ...
            case BINDER_WORK_TRANSACTION: {
                t = container_of(w, struct binder_transaction, work);
            } break;
        }
        if (t->buffer->target_node) {
            struct binder_node *target_node = t->buffer->target_node;
            tr.target.ptr = target_node->ptr;
            tr.cookie =  target_node->cookie;
            t->saved_priority = task_nice(current);
            if (t->priority < target_node->min_priority &&
                !(t->flags & TF_ONE_WAY))
                binder_set_nice(t->priority);
            else if (!(t->flags & TF_ONE_WAY) ||
                 t->saved_priority > target_node->min_priority)
                binder_set_nice(target_node->min_priority);
            cmd = BR_TRANSACTION;                                                                   //cmd = BR_TRANSACTION
        } else {
            tr.target.ptr = NULL;
            tr.cookie = NULL;
            cmd = BR_REPLY;
        }
        ...
        if (put_user(cmd, (uint32_t __user *)ptr))      //把cmd = BR_TRANSACTION写回到用户传进来的缓冲区ptr = bwr.read_buffer，故执行完binder_thread_read后cmd = bwr.read_buffer = BR_TRANSACTION
            return -EFAULT;                                                             即bwr.read_buffer = BR_TRANSACTION
        ptr += sizeof(uint32_t);
        if (copy_to_user(ptr, &tr, sizeof(tr)))             
            return -EFAULT;
        ptr += sizeof(tr);
    }
    return 0;
}
```



###### 2.1.1 总结

分析res = ioctl(bs->fd, BINDER_WRITE_READ, &bwr);可知 bwr.read_buffer = BR_TRANSACTION



##### 2.2 res = binder_parse(bs, 0, (uintptr_t) readbuf, bwr.read_consumed, func);

```c
int binder_parse(struct binder_state *bs, struct binder_io *bio,
                 uintptr_t ptr, size_t size, binder_handler func)
{
    int r = 1;
    uintptr_t end = ptr + (uintptr_t) size;
    while (ptr < end) {
        uint32_t cmd = *(uint32_t *) ptr;
        ptr += sizeof(uint32_t);
        switch(cmd) {
        ...
        case BR_TRANSACTION: {
            struct binder_transaction_data *txn = (struct binder_transaction_data *) ptr;       //由ptr构造binder_transaction_data结构体txn
            if ((end - ptr) < sizeof(*txn)) {
                ALOGE("parse: txn too small!\n");
                return -1;
            }
            binder_dump_txn(txn);
            if (func) {                                     //func为binder_handler函数指针
                unsigned rdata[256/4];
                struct binder_io msg;
                struct binder_io reply;
                int res;
                bio_init(&reply, rdata, sizeof(rdata), 4);          //接收到数据之后，构造一个binder_io结构体reply
                bio_init_from_txn(&msg, txn);               //由txn构造一个binder_io结构体msg
                res = func(bs, txn, &msg, &reply);          //调用处理函数 --- 由binder_loop(bs, svcmgr_handler)第二个参数可知func是函数指针binder_handler,这个函数指针指向了svcmgr_handler函数
                binder_send_reply(bs, &reply, txn->data.ptr.buffer, res);       //如果res为0，表示注册成功，代码0写入binder_io结构体reply中
            }
            ptr += sizeof(*txn);
            break;
        }
    }
    return r;
}
struct binder_io{
    char *data              //从binder读取或者写入到binder中的内容指针
    binder_size_t *offs;
    char *data0;            //内容起始位置，用作基准值
    ...
}

void bio_init(struct binder_io *bio, void *data,
              size_t maxdata, size_t maxoffs)
{
    size_t n = maxoffs * sizeof(size_t);        //偏移数组所占的大小
    if (n > maxdata) {                                          //偏移数组所占的大小不能大于最大能分配大小
        bio->flags = BIO_F_OVERFLOW;
        bio->data_avail = 0;
        bio->offs_avail = 0;
        return;
    }
    bio->data = bio->data0 = (char *) data + n;     //bio->data
    bio->offs = bio->offs0 = data;              //开始是偏移数组
    bio->data_avail = maxdata - n;              //数据缓冲区大小
    bio->offs_avail = maxoffs;                      //偏移数组大小
    bio->flags = 0;
}

void bio_init_from_txn(struct binder_io *bio, struct binder_transaction_data *txn)
{
    bio->data = bio->data0 = (char *)(intptr_t)txn->data.ptr.buffer;
    bio->offs = bio->offs0 = (binder_size_t *)(intptr_t)txn->data.ptr.offsets;
    bio->data_avail = txn->data_size;
    bio->offs_avail = txn->offsets_size / sizeof(size_t);
    bio->flags = BIO_F_SHARED;
}

frameworks/native/cmds/servicemanager/Service_manager.c：
int svcmgr_handler(struct binder_state *bs,
                   struct binder_transaction_data *txn,
                   struct binder_io *msg,
                   struct binder_io *reply)
{
    struct svcinfo *si;
    uint16_t *s;
    size_t len;
    uint32_t handle;
    uint32_t strict_policy;
    int allow_isolated;
    if (txn->target.handle != svcmgr_handle)        //txn->target为NULL，svcmgr_handle为NULL(void* (0))
        return -1;
    if (txn->code == PING_TRANSACTION)
        return 0;
    strict_policy = bio_get_uint32(msg);
    s = bio_get_string16(msg, &len);            //返回s = bio->data = "window"
    if (s == NULL) {
        return -1;
    }
    if ((len != (sizeof(svcmgr_id) / 2)) ||
        memcmp(svcmgr_id, s, sizeof(svcmgr_id))) {
        fprintf(stderr,"invalid id %s\n", str8(s, len));
        return -1;
    }
    if (sehandle && selinux_status_updated() > 0) {
        struct selabel_handle *tmp_sehandle = selinux_android_service_context_handle();
        if (tmp_sehandle) {
            selabel_close(sehandle);
            sehandle = tmp_sehandle;
        }
    }
    switch(txn->code) {
    case SVC_MGR_GET_SERVICE:
    case SVC_MGR_CHECK_SERVICE:
        s = bio_get_string16(msg, &len);    //s = "window"
        if (s == NULL) {
            return -1;
        }
        handle = do_find_service(bs, s, len, txn->sender_euid, txn->sender_pid);
        if (!handle)
            break;
        bio_put_ref(reply, handle);
        return 0;
    }
    bio_put_uint32(reply, 0);       //将注册成功代码0写入binder_io结构体reply中
    return 0;
}

uint32_t do_find_service(struct binder_state *bs, const uint16_t *s, size_t len, uid_t uid, pid_t spid)     //s = "window"
{
    struct svcinfo *si;

    if (!svc_can_find(s, len, spid)) {
        return 0;
    }
    si = find_svc(s, len);      //从svclist链表中寻找name = "window"的svcinfo并返回
    if (si && si->handle) {
        if (!si->allow_isolated) {
            uid_t appid = uid % AID_USER;
            if (appid >= AID_ISOLATED_START && appid <= AID_ISOLATED_END) {
                return 0;
            }
        }
        return si->handle;      //返回svcinfo.handle即为name = "window"对应的new WindowManagerService(...)的服务端
    } else {
        return 0;
    }
}

struct svcinfo *find_svc(const uint16_t *s16, size_t len)           //s16 = "window"
{
    struct svcinfo *si;
    for (si = svclist; si; si = si->next) {     //从svclist链表中寻找name = "window"的svcinfo并返回
        if ((len == si->len) &&
            !memcmp(s16, si->name, len * sizeof(uint16_t))) {
            return si;
        }
    }
    return NULL;
}

struct svcinfo
{
    struct svcinfo *next;       //用于形成链表
    uint32_t handle;
    struct binder_death death;
    int allow_isolated;
    size_t len;
    uint16_t name[0];       //用于保存注册的Service组件的名称
};
```



#### 3. ServiceManager获取服务总结：

ServiceManager 服务获得过程例如ServiceManager.getService(“window”);

1. 向ServiceManager的todo队列里面添加一条获得服务”window”的事务
2.  ServiceManager从svclist链表中寻找name = “window”的svcinfo并返回，最终返回svcinfo.handle即为name = “window”对应的new WindowManagerService(…)的服务端


