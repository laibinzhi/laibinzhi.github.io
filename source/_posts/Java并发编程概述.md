---
title: Java并发编程概述
date: 2022-05-05 18:20:37
tags:
  - Android
  - Java  
  - 并发
  - 线程   
---
# Java并发编程

## 进程和线程的区别

### 进程和线程的由来

- **串行**。初期的计算机智能串行执行任务，并且需要长时间等待用户输入。
- **批处理**。预先将用户的指令集中成清单，批量串行处理指令，仍然无法并行执行。
- 进程。进程独占内存空间，保存各自运行状态，相互间不干扰且可以互相切换，为并发处理任务提供了可能。
- 线程。共享进程的内存资源，相互间切换更快捷，支持更细粒度的任务控制，使进程内的子任务得以并发执行。

### 进程是资源分配的最小单元，线程是CPU调度的最小单位

- 所有与进程有关的资源，都被记录在PCB中。
- 进程是抢占处理器的调度单位；线程属于某个进程，共享其资源。
- 线程只由**堆栈寄存器**、**程序计数器**和**TCB**组成。

<!--more-->


### 总结

- 线程不能看做独立应用，而进程可看做独立应用。
- 进程有独立的地址空间，相互不影响，线程只是进程的不同执行路径。
- 线程没有独立的地址空间，多进程的程序比多线程程序健壮。
- 进程的切换比线程的切换开销大。
- 如果一个进程，还有一个线程没有杀掉 还存活，那么进程还存活 （线程依附进程）

## Java进程和线程的关系

- Java对操作系统提供的功能进行封装，包括进程和线程
- 运行一个程序会产生一个进程，进程包含至少一个线程。
- 每个进程对应一个JVM实例，多个线程共享JVM里的堆。
- Java采用单线程编程模型，程序会自动创建主线程。
- 主线程可以创建子线程，原则上要后于子线程完成执行。

## Thread中run和start的区别

Thread#start() ---> JVM_StartThread --->thread_entry ---> Thread#run()

1. 调用***start()***方法会创建一个新的子线程并启用。
2. ***run(*)**方法只是**Thread**的一个普通方法调用，在主线程中执行。

## 创建线程

### 方式1：继承Thread

```Java
public class Main {
    public static void main(String[] args) {
        Thread t = new Thread();
        t.start(); // 启动新线程
    }
}
```



### 方式2：实现Runnable

```Java
public class Main {
    public static void main(String[] args) {
        Thread t = new Thread(new MyRunnable());
        t.start(); // 启动新线程
    }
}

class MyRunnable implements Runnable {
    @Override
    public void run() {
        System.out.println("start new thread!");
    }
}

```



### 方式3：通过Callable和FutureTask接口创建线程。（其实也是属于方式2实现Runnable接口）

```Java
    public static void main(String[] args) throws Exception {
        WorkerThread workerThread = new WorkerThread();
        FutureTask<String> futureTask = new FutureTask<>(workerThread);
        new Thread(futureTask).start();
        System.out.println(futureTask.get());
    }

    private static class WorkerThread implements Callable<String> {
        @Override
        public String call() throws Exception {
            System.out.println("do work WorkerThread");
            Thread.sleep(10000);
            return "run success";
        }
    }
```

### 方式4：通过Callable和线程池创建线程（其实也是属于方式2实现Runnable接口）

### Thread和Runnable是什么关系？

- Thread是实现了Runnable接口的类，使得run支持多线程。
- 因为类的单一继承原则，推荐多使用Runnable接口。

## 如何实现处理线程的返回值

### 主线程等待法

```Java
public class Ttt {
    public static void main(String[] args) throws Exception {
        WorkerThread workerThread = new WorkerThread();
        Thread thread = new Thread(workerThread);
        thread.start();
        while (workerThread.value == null) {
            Thread.sleep(100);
        }
        System.out.println("value=" + workerThread.value);
    }

    private static class WorkerThread implements Runnable {
        private String value;

        @Override
        public void run() {
            try {
                Thread.sleep(5000);
            } catch (InterruptedException e) {
                e.printStackTrace();
            }
            value = "现在有值了";
        }
    }
}

```

- 优点：实现简单。
- 缺点：需要自己实现循环等待的逻辑，当需要等待的变量一多，代码异常臃肿，while写很多变量。更重要需要循环多久不确定，没办法精准控制。

### 使用Thread类的join()阻塞当前线程以等待子线程处理完毕

```Java
 public static void main(String[] args) throws Exception {
        WorkerThread workerThread = new WorkerThread();
        Thread thread = new Thread(workerThread);
        thread.start();
//        while (workerThread.value == null) {
//            Thread.sleep(100);
//        }
        thread.join();
        System.out.println("value=" + workerThread.value);
    }
```

- 优点：能够比主线程等待法更简单，更加精准控制。
- 缺点：力度不够细。更精准的依赖关系join是没办法实现。

### 通过Callable接口实现：通过FutureTask或者是线程池获取

#### 通过FutureTask

```Java
  public static void main(String[] args) throws Exception {
        WorkerThread workerThread = new WorkerThread();
        FutureTask<String> futureTask = new FutureTask<>(workerThread);
        Thread thread = new Thread(futureTask);
        thread.start();
        if (!futureTask.isDone()){
            System.out.println("程序还没执行完成，请等待");
        }
        System.out.println("程序执行完成，value=" + futureTask.get());
    }

    private static class WorkerThread implements Callable<String> {

        @Override
        public String call() throws Exception {
            System.out.println("我是程序，程序就绪工作完成");
            String value = "123";
            Thread.sleep(5000L);
            System.out.println("我是程序，程序赋值工作已经完成");
            return value;
        }
    }
```



#### 通过线程池

```Java
public class Ttt {
    public static void main(String[] args) {
        WorkerThread workerThread = new WorkerThread();
        ExecutorService executorService = Executors.newCachedThreadPool();
        Future<String> future = executorService.submit(workerThread);
        if (!future.isDone()) {
            System.out.println("程序还没执行完成，请等待");
        }
        try {
            System.out.println("程序执行完成，value=" + future.get());
        } catch (InterruptedException | ExecutionException e) {
            e.printStackTrace();
        } finally {
            executorService.shutdown();
        }
    }

    private static class WorkerThread implements Callable<String> {

        @Override
        public String call() throws Exception {
            System.out.println("我是程序，程序就绪工作完成");
            String value = "123";
            Thread.sleep(5000L);
            System.out.println("我是程序，程序赋值工作已经完成");
            return value;
        }
    }
}


```

#### 对比

使用线程池的方式好处：提交多个实现Callable方法的类让线程池并发处理结果，这样更方便统一管理。



## 线程的状态

#### 简述

1. **新建（New）**：创建后尚未启动线程的状态。

2. **运行（Runnable）**：包含Running和Ready。

3. **阻塞（Blocked）**：运行中的线程，因为某些操作被阻塞而挂起，等待获取排它锁。（阻塞状态是线程阻塞在进入synchronized关键字修饰的方法或代码块(获取锁)时的状态。）

4. **无限期等待（Waiting）**：不会被分配cpu执行时间，需要显式被唤醒。

   > 以下的方法会使线程进入无限期等待：
   >
   > 1. 没有设置Timeout参数的***Object.wait()***。
   > 2. 没有设置Timeout参数的***Thread.join()***。
   > 3. ***Locksupport.park()***。

5. **限期等待（Timed Waiting）**：在一定时间后系统会唤醒。

   > 以下的方法会使线程进入限期等待：
   >
   > 1. ***Thread.sleep()***
   > 2. 设置Timeout参数的***Object.wait()***
   > 3. 设置Timeout参数的***Thread.join()***
   > 4. ***Locksupport.parkNanou(long)***
   > 5. ***Locksupport.parkUtil(long)***

   

6. 结束（Terminated）：已终止线程的状态，线程已经结束执行。

#### 图解

https://blog.csdn.net/u014454538/article/details/121190001

参考https://blog.51cto.com/u_15060546/3921436

![image](https://s2.loli.net/2022/05/04/aPNuMcg2G84zjJh.png)

![image](https://s2.loli.net/2022/05/04/cZOIRLWYfw4etV5.png)

## sleep和wait的区别

- sleep()是Thread类的方法，wait()是Object类中定义的方法。
- sleep()方法可以在任何地方使用。
- wait()方法只能在synchronized方法或者synchronized块中使用。
- sleep在抛出异常的时候，捕获异常之前，就已经清除中断标志。
- 最主要的本地区别
  - Thread.sleep只会让出CPU，不会导致锁行为的改变。
  - Object.wait不仅让出CPU，还会释放已经占有的同步资源锁。

## notify和notifyAll的区别

### 锁池EntryList

假设线程A已经拥有了某个对象（不是类）的锁，而其他线程B、C想要调用这个对象的某个synchronized方法（或者块），由于B、C线程在进入的synchronized方法（或者块）之前必须先获得该对象锁的拥有权，而恰巧该对象的锁目前正在被线程A所占用，此时B、C线程就会被阻塞，进入一个地方去等待锁的释放，这个地方便是该对象的锁池。

### 等待池WitSet

假设线程A调用了某个对象的wait()方法，线程A就会释放该对象的锁，同时线程A就进入到了该对象的等待池中，进入到等待池中的线程不会去竞争该对象的锁。

### notifyAll

notifyAll会让所有处于等待池的线程全部进入锁池去竞争获取锁的机会。

### notify

notify只会随机选取一个处于等待池中的线程进入锁池去竞争获取锁的机会。

## wait/notify机制

当线程执行wait()方法时候，会释放当前的锁，然后让出CPU，进入等待状态。
只有当 notify/notifyAll() 被执行时候，才会唤醒一个或多个正处于等待状态的线程，然后继续往下执行，直到执行完synchronized 代码块的代码或是中途遇到wait() ，再次释放锁。

https://blog.csdn.net/y277an/article/details/98697454

![image](https://s2.loli.net/2022/05/04/FHcICOSb9De6fVh.jpg)

**等待/通知机制，是指线程A调用了对象O的wait()方法进入等待状态，而线程B调用了对象O的notify()/notifyAll()方法，线程A收到通知后退出等待队列，进入可运行状态，进而执行后续操作。 上述两个线程通过对象O来完成交互，而对象上的wait()方法和notify()/notifyAll()方法的关系就如同开关信号一样，用来完成等待方和通知方之间的交互工作。**

## yield礼让线程

当调用Thread.yield()函数时，会给线程调度器一个当前线程愿意让出CPU使用的暗示，但是线程调度器可能会忽略这个暗示。

## 中断线程

### 已经被抛弃的方法

通过调用stop()方法停止线程。不推荐

- 线程执行stop()方法，会立即终止run()方法，可能会导致一些清理性工作未能完成，比如数据库关闭等；

- 执行stop()方法后，线程会立即释放持有的所有锁，可能会导致数据同步出现问题；

### 目前使用的方法

1. 调用***interrupt()***，通知线程应该中断了.
   - 如果线程处于被阻塞状态，那么线程将立即退出被阻塞状态，并抛出一个InterruptedExcaption异常。
   - 如果线程处于正常活动状态，那么会将该线程的中断标志设置为true。被设置中断标志的线程将继续正常运行，不受影响。
2. 需要被调用的线程配合中断
   - 在正常运行任务时，经常检查本线程中的中断标志位，如果被设置了中断标志就自行停止线程。
   - 如果线程处于正常活动状态，那么会将该线程的中断标志设置为true。被设置中断标志的线程将继续正常运行，不受影响。

3. Java中断只是将处于RUNNABLE、TIMED_WAITING、WAITING、BLOCKED状态下的线程的中断标记位置为true，不过Java中断会额外对处于TIMED_WAITING、WAITING状态的线程会将其切换为RUNNABLE状态继续执行，处于BLOCKED状态的线程仍然处于BLOCKED状态。

## 死锁

- 规范定义：死锁是指两个或两个以上的进程在执行过程中，由于竞争资源或者由于彼此通信而造成的一种阻塞的现象，若无外力作用，它们都将无法推进下去。此时称系统处于死锁状态或系统产生了死锁。

- 产生死锁的必要条件：
  - 多个操作者（M》=2）去争夺多个资源（N》=2）。N《=M
  - 争夺资源的顺序不对
  - 拿到资源不放手

- 术语
  - 互斥条件
  - 请求保持
  - 不剥夺
  - 环路等待

## ThreadLocal

https://www.cnblogs.com/dennyzhangdd/p/7978455.html

- **线程本地变量**，也有些地方叫做**线程本地存储**，其实意思差不多。ThreadLocal可以让每个线程拥有一个属于自己的变量的副本，不会和其他线程的变量副本冲突，实现了线程的数据隔离。

- ThreadLocal不是用来解决线程安全问题的，多线程不共享，不存在竞争！目的是线程本地变量且只能单个线程内维护使用。

### 源码分析

#### getMap()

**ThreadLocalMap**是ThreadLocal的一个内部类。

> ThreadLocalMap是一个定制的哈希映射，仅适用于维护线程本地值。ThreadLocalMap类是包私有的，允许在Thread类中声明字段。为了帮助处理非常大且长时间的使用，哈希表entry使用了对键的弱引用。有助于GC回收。

- 通过getMap()获取每个子线程Thread持有自己的ThreadLocalMap实例, 因此它们是不存在并发竞争的。可以理解为每个线程有自己的变量副本。
- ThreadLocalMap中Entry[]数组存储数据，初始化长度**16**，后续每次都是**2倍**扩容。主线程中定义了几个变量，Entry[]才有几个key。
- Entry的key是对ThreadLocal的**弱引用**，当抛弃掉ThreadLocal对象时，垃圾收集器会忽略这个key的引用而清理掉ThreadLocal对象， 防止了内存泄漏。

#### set()

1. 根据哈希码和数组长度求元素放置的位置，即数组下标

2. 从第一步得出的下标开始往后遍历，如果key相等，覆盖value，如果key为null,用新key、value覆盖，同时清理历史key=null的陈旧数据
3. 如果超过阀值，就需要再哈希：
   - 清理一遍陈旧数据。 
   - \>= 3/4阀值,就执行扩容，把table扩容2倍==》注意这里3/4阀值就执行扩容，避免迟滞。
   - 把老数据重新哈希散列进新table。

#### get()

1. 从当前线程中获取ThreadLocalMap，查询当前ThreadLocal变量实例对应的Entry，如果不为null,获取value,返回。
2. 如果map为null,即还没有初始化，走初始化方法。
3. 用户可以自定义initialValue()初始化方法，来初始化threadLocal的值。

#### Remove()

参考https://www.cnblogs.com/Ccwwlx/p/13581004.html

```Java
private void remove(ThreadLocal<?> key) {
    //使用hash方式，计算当前ThreadLocal变量所在table数组位置
    Entry[] tab = table;
    int len = tab.length;
    int i = key.threadLocalHashCode & (len-1);
    //再次循环判断是否在为ThreadLocal变量所在table数组位置
    for (Entry e = tab[i];
         e != null;
         e = tab[i = nextIndex(i, len)]) {
        if (e.get() == key) {
            //调用WeakReference的clear方法清除对ThreadLocal的弱引用
            e.clear();
            //清理key为null的元素
            expungeStaleEntry(i);
            return;
        }
    }
}
```

```Java
private int expungeStaleEntry(int staleSlot) {
    Entry[] tab = table;
    int len = tab.length;
​
    // 根据强引用的取消强引用关联规则，将value显式地设置成null，去除引用
    tab[staleSlot].value = null;
    tab[staleSlot] = null;
    size--;
​
    // 重新hash，并对table中key为null进行处理
    Entry e;
    int i;
    for (i = nextIndex(staleSlot, len);
         (e = tab[i]) != null;
         i = nextIndex(i, len)) {
        ThreadLocal<?> k = e.get();
        //对table中key为null进行处理,将value设置为null，清除value的引用
        if (k == null) {
            e.value = null;
            tab[i] = null;
            size--;
        } else {
            int h = k.threadLocalHashCode & (len - 1);
            if (h != i) {
                tab[i] = null;
                while (tab[h] != null)
                    h = nextIndex(h, len);
                tab[h] = e;
            }
        }
    }
    return i;
}
```



### InheritableThreadLocal

这个类扩展ThreadLocal，以提供从父线程到子线程的值的继承:当创建子线程时，子线程会接收父元素所具有值的所有可继承线程局部变量的初始值。正常情况下，子线程的变量值与父线程的相同;然而，子线程可复写childValue方法来自定义获取父类变量。
当变量(例如，用户ID、事务ID)中维护的每个线程属性必须自动传输到创建的任何子线程时，使用InheritableThreadLocal优于ThreadLocal。

1. 子线程根据childValue函数获取到了父线程的变量值。
2. 多线程InheritableThreadLocal变量各自维护，无竞争关系

### 内存泄漏

#### 出现原因

hreadLocalMap使用ThreadLocal的弱引用作为key，如果一个ThreadLocal不存在外部强引用时，Key(ThreadLocal)势必会被GC回收，这样就会导致ThreadLocalMap中key为null， 而value还存在着强引用，只有thead线程退出以后,value的强引用链条才会断掉。

但如果当前线程再迟迟不结束的话，这些key为null的Entry的value就会一直存在一条强引用链：

> Thread Ref -> Thread -> ThreaLocalMap -> Entry -> value

永远无法回收，造成内存泄漏。



那为什么使用弱引用而不是强引用？？

- key使用强引用

  当threadLocalMap的key为强引用回收ThreadLocal时，因为ThreadLocalMap还持有ThreadLocal的强引用，如果没有手动删除，ThreadLocal不会被回收，导致Entry内存泄漏。

- key使用弱引用

  当ThreadLocalMap的key为弱引用回收ThreadLocal时，由于ThreadLocalMap持有ThreadLocal的弱引用，即使没有手动删除，ThreadLocal也会被回收。当key为null，在下一次ThreadLocalMap调用set(),get()，remove()方法的时候会被清除value值。

#### 总结

- 由于Thread中包含变量ThreadLocalMap，因此ThreadLocalMap与Thread的生命周期是一样长，如果都没有手动删除对应key，都会导致内存泄漏。

- 但是使用**弱引用**可以多一层保障：弱引用ThreadLocal不会内存泄漏，对应的value在下一次ThreadLocalMap调用set(),get(),remove()的时候会被清除。

- 因此，ThreadLocal内存泄漏的根源是：由于ThreadLocalMap的生命周期跟Thread一样长，如果没有手动删除对应key就会导致内存泄漏，而不是因为弱引用。

#### ThreadLocal正确使用方法

- 每次使用完ThreadLocal都调用它的***remove()***方法清除数据
- 将ThreadLocal变量定义成private static，这样就一直存在ThreadLocal的强引用，也就能保证任何时候都能通过ThreadLocal的弱引用访问到Entry的value值，进而清除掉 。



## CAS(Compare And Swap)

### 一，CAS原理

CAS 全称是 **compare and swap**，是一种用于在多线程环境下实现同步功能的机制。CAS 操作包含三个操作数 -- 内存地址、预期数值和新值。CAS 的实现逻辑是将内存位置处的数值与预期数值想比较，若相等，则将内存位置处的值替换为新值。若不相等，则不做任何操作。

### 二，CAS的问题

#### 1.ABA问题

一个线程a将数值改成了b，接着又改成了a，此时CAS认为是没有变化，其实是已经变化过了，而这个问题的解决方案可以使用版本号标识，每操作一次version加1。在java5中，已经提供了AtomicStampedReference来解决问题。

#### 2.开销问题

CAS造成CPU利用率增加。之前说过了CAS里面是一个循环判断的过程，如果线程一直没有获取到状态，cpu资源会一直被占用。

#### 3.只能保证一个共享变量的原子操作

可以把多个变量放在一个对象AtomicReference里来进行CAS操作。

### 三，Java提供的原子类

- 更新基本类型类：AtomicBoolean，AtomicInteger，AtomicLong
- 更新数组类：AtomicIntegerArray，AtomicLongArray，AtomicReferenceArray

- 更新引用类型：AtomicReference，**AtomicMarkableReference**( 不关心修改过几次，仅仅关心是否修改过，布尔类型)，**AtomicStampedReference**（知道修改了几次）

## 阻塞队列

https://www.cnblogs.com/i-code/p/13983419.html

### 定义

- 当阻塞队列是空时，从队列中获取元素的操作将会被阻塞。
- 当阻塞队列是满时，从队列中添加元素的操作将会被阻塞。
- 常用于生产者消费者模型。

### 用处（好处）

好处是我们不需要关心什么时候需要阻塞线程，什么时候需要唤起线程，因为这一切BlockingQueue都给你一手包办了。

在concurrent包发布以前，在多线程环境下，我们每个程序员必须去自己控制这些细节，尤其还要兼顾效率和线程安全，而这会给我们的程序带来不小的复杂度。

### 分类

http://concurrent.redspider.group/article/03/13.html

JDK 提供了 7 个阻塞队列。分别是

- **ArrayBlockingQueue** ：一个由**数组**结构组成的**有界**阻塞队列

  > 构造方法中的fair表示控制对象的内部锁是否采用公平锁，默认是**非公平锁**。

- **LinkedBlockingQueue** ：一个由**链表**结构组成的**有界**阻塞队列。

  > 默认队列的大小是`Integer.MAX_VALUE`，也可以指定大小。此队列按照**先进先出**的原则对元素进行排序

- PriorityBlockingQueue ：一个支持优先级排序的**无界**阻塞队列。

  > 基于优先级的无界阻塞队列（优先级的判断通过构造函数传入的Compator对象来决定），内部控制线程同步的锁采用的是**非公平锁**。

- DelayQueue：一个使用优先级队列实现的**无界**阻塞队列

  > 该队列中的元素只有当其指定的延迟时间到了，才能够从队列中获取到该元素 。注入其中的元素必须实现 java.util.concurrent.Delayed 接口。 
  >
  > DelayQueue是一个没有大小限制的队列，因此往队列中插入数据的操作（生产者）永远不会被阻塞，而只有获取数据的操作（消费者）才会被阻塞。

- **SynchronousQueue**：一个不存储元素的阻塞队列。

  > 这个队列比较特殊，没有任何内部容量，甚至连一个队列的容量都没有。并且每个 put 必须等待一个 take，反之亦然。

- LinkedTransferQueue：一个由链表结构组成的无界阻塞队列（实现了继承于 BlockingQueue 的 TransferQueue）。

- LinkedBlockingDeque：一个由链表结构组成的双向阻塞队列。

### 方法

|  **分类**  | **方法** |          **含义**          |                          **特点**                          |
| :--------: | :------: | :------------------------: | :--------------------------------------------------------: |
|  抛出异常  |   add    |        添加一个元素        |   如果队列已满，添加则抛出 `IllegalStateException` 异常    |
|            |  remove  |       删除队列头节点       |   当队列为空后，删除则抛出 `NoSuchElementException` 异常   |
|            | element  |       获取队列头元素       |     当队列为空时，则抛出 `NoSuchElementException` 异常     |
| 返回无异常 |  offer   |        添加一个元素        | 当队列已满，不会报异常，返回 `false` ，如果成功返回 `true` |
|            |   poll   | 获取队列头节点，并且删除它 |                  当队列空时，返回 `Null`                   |
|            |   peek   |       单纯获取头节点       |                  当队列为空时反馈 `NULL`                   |
|    阻塞    |   put    |        添加一个元素        |                     如果队列已满则阻塞                     |
|            |   take   |      返回并删除头元素      |                     如果队列为空则阻塞                     |



## 线程池

### 定义和好处

1. 降低资源消耗（通过重复利用已经创建的线程来减低线程创建销毁所带来的的消耗）
2. 提高响应速度（任务可以不需等到线程创建就立即执行）
3. 提高线程的可管理性（稳定）

### 7个参数

- **corePoolSize**： 核心线程数
- **maximumPoolSize**：最大线程数
- **keepAliveTime**：非核心线程存活时间
- **unit**：非核心线程存活时间单位
- **BlockingQueue**：缓存阻塞队列
  - ArrayBlockingQueue：基于数组结构的有界阻塞队列，按FIFO排序任务；
  - LinkedBlockingQuene：基于链表结构的阻塞队列，按FIFO排序任务，吞吐量通常要高于ArrayBlockingQuene；
  - SynchronousQuene：一个不存储元素的阻塞队列，每个插入操作必须等到另一个线程调用移除操作，否则插入操作一直处于阻塞状态，吞吐量通常要高于LinkedBlockingQuene；
  - priorityBlockingQuene：具有优先级的无界阻塞队列；

- **threadFactory**：线程工厂（主要是命名）
- **RejectedExecutionHandler**：拒绝策略
  - AbortPolicy：直接抛出异常，默认策略。
  -  CallerRunsPolicy：只要线程池没有关闭，该策略直接在调用者线程中，执行当前被丢弃的任务。
  -  DiscardOldestPolicy：丢弃最老的一个请求（任务队列里面的第一个），再尝试提交任务。
  - DiscardPolicy：直接啥事都不干，直接把任务丢弃。
  - 当然也可以根据应用场景实现RejectedExecutionHandler接口，自定义饱和策略，如记录日志或持久化存储不能处理的任务。

### Java提供的常用配置线程池

- newSingleThreadExecutor()

  ```Java
     public static ExecutorService newSingleThreadExecutor() {
          return new FinalizableDelegatedExecutorService
              (new ThreadPoolExecutor(1, 1,
                                      0L, TimeUnit.MILLISECONDS,
                                      new LinkedBlockingQueue<Runnable>()));
      }
  ```

  

- newFixedThreadPool()

  ```Java
    public static ExecutorService newFixedThreadPool(int nThreads) {
          return new ThreadPoolExecutor(nThreads, nThreads,
                                        0L, TimeUnit.MILLISECONDS,
                                        new LinkedBlockingQueue<Runnable>());
      }
  ```

  

- newScheduledThreadPool()

  ```Java
   public ScheduledThreadPoolExecutor(int corePoolSize) {
          super(corePoolSize, Integer.MAX_VALUE, 0, NANOSECONDS,
                new DelayedWorkQueue());
      }
  
  ```

  

- newCachedThreadPoo()

  ```Java
      public static ExecutorService newCachedThreadPool() {
          return new ThreadPoolExecutor(0, Integer.MAX_VALUE,
                                        60L, TimeUnit.SECONDS,
                                        new SynchronousQueue<Runnable>());
      }
  
  ```

- 不建议使用Executors创建

  1. newSingleThreadExecutor，newFixedThreadPool允许请求队列长度为Integer.MAX_VALUE，可能会堆积**大量的请求**。从而导致OOM。
  2. newScheduledThreadPool和newCachedThreadPoo允许创建线程数量为Integer.MAX_VALUE。可能会创建**大量的线程**，从而导致OOM。

  

### 合理配置线程池

CPU密集型任务：尽量压榨CPU，参考值设置为CPU的个数+1
IO密集型任务：参考值可以设置为CPU的个数 * 2

### 线程池工作流程

![image](https://s2.loli.net/2022/05/04/OX1c6gZLha4rGiB.png)

![image](https://s2.loli.net/2022/05/04/eSibKLuhG8OD4go.png)



## AQS

### 学习AQS的必要性

队列同步器**AbstractQueuedSynchronizer**（以下简称同步器或**AQS**），**是用来构建锁或者其他同步组件的基础框架**，它使用了一个int成员变量表示同步状态，通过内置的FIFO队列来完成资源获取线程的排队工作。

### AQS使用方法和其中的设计模式

AQS的主要使用方式是**继承**，子类通过继承AQS并实现它的抽象方法来管理同步状态，在AQS里由一个int型的state来代表这个状态，在抽象方法的实现过程中免不了要对同步状态进行更改，这时就需要使用同步器提供的3个方法（**getState()**、**setState(int newState)**和**compareAndSetState(int expect,int update)**）来进行操作，因为它们能够保证状态的改变是安全的。



在实现上，子类推荐被定义为自定义同步组件的静态内部类，AQS自身没有实现任何同步接口，它仅仅是定义了若干同步状态获取和释放的方法来供自定义同步组件使用，同步器既可以支持独占式地获取同步状态，也可以支持共享式地获取同步状态，这样就可以方便实现不同类型的同步组件（**ReentrantLock**、ReentrantReadWriteLock和**CountDownLatch**等）。

#### 模板方法模式

### CLH队列锁

CLH队列锁也是一种基于**链表**的可扩展、高性能、**公平**的**自旋锁**，申请线程仅仅在本地变量上自旋，它不断轮询前驱的状态，假设发现前驱释放了锁就结束自旋。

当一个线程需要获取锁时：

1. 创建一个的QNode，将其中的locked设置为true表示需要获取锁，myPred表示对其前驱结点的引用。

   ![image](https://s2.loli.net/2022/05/01/z9UmN5aSyosc7If.png)

2. 线程A对tail域调用getAndSet方法，使自己成为队列的尾部，同时获取一个指向其前驱结点的引用myPred。

   ![image](https://s2.loli.net/2022/05/01/CINSDlbOp9uw4Hz.png)

   线程B需要获得锁，同样的流程再来一遍

   ![image](https://s2.loli.net/2022/05/01/UlYwQsbpMG5ixyV.png)

3. 线程就在前驱结点的locked字段上旋转，直到前驱结点释放锁(前驱节点的锁值 locked == false)。
4. 当一个线程需要释放锁时，将当前结点的locked域设置为false，同时回收前驱结点。

![image](https://s2.loli.net/2022/05/01/KVdBj6S8DLvw2FU.png)

如上图所示，前驱结点释放锁，线程A的myPred所指向的前驱结点的locked字段变为false，线程A就可以获取到锁。

- CLH队列锁的优点是空间复杂度低（如果有n个线程，L个锁，每个线程每次只获取一个锁，那么需要的存储空间是O（L+n），n个线程有n个myNode，L个锁有L个tail）。CLH队列锁常用在SMP体系结构下。

- Java中的AQS是CLH队列锁的一种变体实现。

## ReentrantLock的实现

### 锁的可重入

重进入是指任意线程在获取到锁之后能够再次获取该锁而不会被锁所阻塞，该特性的实现需要解决以下两个问题。

1. 线程再次获取锁。锁需要去识别获取锁的线程是否为当前占据锁的线程，如果是，则再次成功获取。
2. 锁的最终释放。线程重复n次获取了锁，随后在第n次释放该锁后，其他线程能够获取到该锁。锁的最终释放要求锁对于获取进行计数自增，计数表示当前锁被重复获取的次数，而锁被释放时，计数自减，当计数等于0时表示锁已经成功释放。

nonfairTryAcquire方法增加了再次获取同步状态的处理逻辑：通过判断当前线程是否为获取锁的线程来决定获取操作是否成功，如果是获取锁的线程再次请求，则将同步状态值进行增加并返回true，表示获取同步状态成功。同步状态表示锁被一个线程重复获取的次数。

如果该锁被获取了n次，那么前(n-1)次tryRelease(int releases)方法必须返回false，而只有同步状态完全释放了，才能返回true。可以看到，该方法将同步状态是否为0作为最终释放的条件，当同步状态为0时，将占有线程设置为null，并返回true，表示释放成功。

```java
   /* 当状态为0的时候获取锁*/
        public boolean tryAcquire(int acquires) {
            if (compareAndSetState(0, 1)) {
                setExclusiveOwnerThread(Thread.currentThread());
                return true;
            }else if(getExclusiveOwnerThread()==Thread.currentThread()){
                setState(getState()+1);
                return  true;
            }
            return false;
        }

        /* 释放锁，将状态设置为0*/
        protected boolean tryRelease(int releases) {
            if(getExclusiveOwnerThread()!=Thread.currentThread()){
                throw new IllegalMonitorStateException();
            }
            if (getState() == 0)
                throw new IllegalMonitorStateException();

            setState(getState()-1);
            if(getState()==0){
                setExclusiveOwnerThread(null);
            }
            return true;
        }
```



### 公平和非公平锁

**ReentrantLock**的构造函数中，默认的无参构造函数将会把Sync对象创建为**NonfairSync**对象，这是一个“非公平锁”；而另一个构造函数**ReentrantLock(boolean fair)**传入参数为true时将会把Sync对象创建为“公平锁”FairSync。

**nonfairTryAcquire(int acquires)**方法，对于非公平锁，只要CAS设置同步状态成功，则表示当前线程获取了锁，而公平锁则不同。tryAcquire方法，该方法与**nonfairTryAcquire(int acquires)**比较，唯一不同的位置为判断条件多了**hasQueuedPredecessors**()方法，即加入了同步队列中当前节点是否有前驱节点的判断，如果该方法返回true，则表示有线程比当前线程更早地请求获取锁，因此需要等待前驱线程获取并释放锁之后才能继续获取锁。

```java
    static final class FairSync extends Sync {
        private static final long serialVersionUID = -3000897897090466540L;

        final void lock() {
            acquire(1);
        }

        /**
         * 和非公平锁的区别就是多了已一个hasQueuedPredecessors方法
         */
        protected final boolean tryAcquire(int acquires) {
            final Thread current = Thread.currentThread();
            int c = getState();
            if (c == 0) {
                if (!hasQueuedPredecessors() &&
                    compareAndSetState(0, acquires)) {
                    setExclusiveOwnerThread(current);
                    return true;
                }
            }
            else if (current == getExclusiveOwnerThread()) {
                int nextc = c + acquires;
                if (nextc < 0)
                    throw new Error("Maximum lock count exceeded");
                setState(nextc);
                return true;
            }
            return false;
        }
    }

```

## Java内存模型（JMM）

### 定义

从抽象的角度来看，JMM定义了线程和主内存之间的抽象关系：线程之间的共享变量存储在主内存（Main Memory）中，每个线程都有一个***私有***的本地内存（Local Memory），本地内存中存储了该线程以读/写共享变量的副本。本地内存是JMM的一个**抽象**概念，并不真实存在。它涵盖了缓存、写缓冲区、寄存器以及其他的硬件和编译器优化。



**关于JMM的一些同步的约定**

1. 线程解锁前，必须把共享变量立刻刷回主内存。
2. 线程加锁前，必须读取主存中的最新值到工作内存中。
3. 加锁和解锁是同1把锁。

### 流程

**线程《==》工作内存《==》save和load操作《==》主存**

![image](https://s2.loli.net/2022/05/04/HGtPyiF4demflAa.png)



#### 主内存与工作内存交互的八种操作

- read(读取)：从主内存读取数据

- load(载入)：将主内存读取到的数据写入工作内存

- use(使用)：从工作内存读取数据来计算

- assign(赋值)：将计算好的值重新赋值到工作内存中

- store(存储)：将工作内存数据写入主内存

- write(写入)：将store过去的变量值赋值给主内存中的变量

- lock(锁定)：将主内存变量加锁，标识为线程独占状态

- unlock(解锁)：将主内存变量解锁，解锁后其他线程可以锁定该变量


![image](https://s2.loli.net/2022/05/04/WI7LXxZM6yC521c.png)

#### **此外，Java内存模型还规定了在上述八种操作时，必须满足下面的规则：**

- 不允许read和load、store与write操作之一单独出现

- 不允许一个线程丢弃它的最近的assign操作，即变量在工作内存中改变之后必须把该变化同步回主内存

- 不允许一个线程无原因（没发生过assign操作）把数据从线程的工作内存中同步回主内存中

- 一个新的变量只能在主内存中诞生，不允许工作内存中直接使用一个未被初始化的变量（也就是说，在变量use、store之前必须经过assign与load操作）

- 一个变量在同一时刻只允许一条线程对其进行lock操作，但是lock操作可以被同一条线程执行多次（lock多少次也必须unlock多少次，才能解锁）

- 如果对一个变量执行lock操作，那么会清空工作内存中此变量的值，在执行引擎使用这个变量前，需要重新执行load或者assign操作初始化变量的值

- 如果一个变量事先没有被lock操作锁定，那么久不允许对它执行unlock操作

- 对一个变量执行unlock操作之前，必须把这个遍历同步回主内存中

### 可见性

可见性是指当多个线程访问同一个变量时，一个线程修改了这个变量的值，其他线程能够立即看得到修改的值。

由于线程对变量的所有操作都必须在工作内存中进行，而不能直接读写主内存中的变量，那么对于共享变量V，它们首先是在自己的工作内存，之后再同步到主内存。可是并不会及时的刷到主存中，而是会有一定时间差。很明显，这个时候线程 A 对变量 V 的操作对于线程 B 而言就不具备可见性了 。

要解决共享对象可见性这个问题，我们可以使用**volatile**关键字或者是加**锁**。



### 原子性

**原子性：即一个操作或者多个操作 要么全部执行并且执行的过程不会被任何因素打断，要么就都不执行。**

我们都知道CPU资源的分配都是以线程为单位的,并且是分时调用,操作系统允许某个进程执行一小段时间，例如 50 毫秒，过了 50 毫秒操作系统就会重新选择一个进程来执行（我们称为“任务切换”），这个 50 毫秒称为“时间片”。而任务的切换大多数是在时间片段结束以后,

那么线程切换为什么会带来bug呢？因为操作系统做任务切换，可以发生在任何一条CPU 指令执行完！注意，是 CPU 指令，CPU 指令，CPU 指令，而不是高级语言里的一条语句。比如count++，在java里就是一句话，但高级语言里一条语句往往需要多条 CPU 指令完成。其实count++至少包含了三个CPU指令！



### 指令重排序

一个好的内存模型实际上会放松对处理器和编译器规则的束缚，也就是说软件技术和硬件技术都为同一个目标而进行奋斗：在不改变程序执行结果的前提下，尽可能提高并行度。JMM对底层尽量减少约束，使其能够发挥自身优势。因此，在执行程序时，**为了提高性能，编译器和处理器常常会对指令进行重排序**。一般重排序可以分为如下三种：

![image](https://s2.loli.net/2022/05/04/fMItZp6ojDqFYx5.png)



### 先行发生原则happens-before

如果A happens-before B，那么Java内存模型将向程序员保证——A操作的结果将对B可见，且A的执行顺序排在B之前。注意，这只是Java内存模型向程序员做出的保证！



两个操作之间存在happens-before关系，并不意味着一定要按照happens-before原则制定的顺序来执行。如果重排序之后的执行结果与按照happens-before关系来执行的结果一致，那么这种重排序并不非法。

- 程序次序规则：同一个线程内，按照代码出现的顺序，前面的代码先行于后面的代码，准确的说是控制流顺序，因为要考虑到分支和循环结构。
- 线程锁定规则：一个unlock操作先行发生于后面（时间上）对同一个锁的lock操作。
- volatile变量规则：对一个volatile变量的写操作先行发生于后面（时间上）对这个变量的读操作
- 线程启动规则：Thread的start( )方法先行发生于这个线程的每一个操作。
- 线程终止规则：线程的所有操作都先行于此线程的终止检测。可以通过Thread.join( )方法结束、Thread.isAlive( )的返回值等手段检测线程的终止。
- 线程中断规则：对线程interrupt( )方法的调用先行发生于被中断线程的代码检测到中断事件的发生，可以通过Thread.interrupt( )方法检测线程是否中断
- 对象终结规则：一个对象的初始化完成先行于发生它的finalize（）方法的开始。
- 传递性：如果操作A先行于操作B，操作B先行于操作C，那么操作A先行于操作C。

## Volatile

### 定义（最轻量级的同步机制）

- 当对volatile变量执行写操作后，JMM会把工作内存中的最新变量值强制刷新到主内存
- 写操作会导致其他线程中的缓存无效

### 特性

1. **保证可见性**
2. **不保证原子性**
3. **禁止指令重排序**

### 实现的底层原理

volatile关键字修饰的变量会存在一个“**lock**:”的前缀指令

Lock前缀，Lock不是一种**内存屏障**，但是它能完成类似内存屏障的功能。Lock会对CPU总线和高速缓存加锁，可以理解为CPU指令级的一种锁。

同时该指令会将当前处理器缓存行的数据直接写会到系统内存中，且这个写回内存的操作会使在其他CPU里缓存了该地址的数据无效。



## synchronized

### 实现原理

**Synchronized**在JVM里的实现都是基于进入和退出**Monitor**对象来实现方法同步和代码块同步，虽然具体实现细节不一样，但是都可以通过成对的**MonitorEnter**和**MonitorExit**指令来实现。

对同步块，**MonitorEnter**指令插入在同步代码块的开始位置，当代码执行到该指令时，将会尝试获取该对象Monitor的所有权，即尝试获得该对象的锁，而monitorExit指令则插入在方法结束处和异常处，JVM保证每个**MonitorEnter**必须有对应的**MonitorExit**。

对同步方法，从同步方法反编译的结果来看，方法的同步并没有通过指令monitorenter和monitorexit来实现，相对于普通方法，其常量池中多了***ACC_SYNCHRONIZED***标示符。

JVM就是根据该标示符来实现方法的同步的：当方法被调用时，调用指令将会检查方法的 ***ACC_SYNCHRONIZED*** 访问标志是否被设置，如果设置了，执行线程将先获取monitor，获取成功之后才能执行方法体，方法执行完后再释放monitor。在方法执行期间，其他任何线程都无法再获得同一个monitor对象。

synchronized使用的锁是存放在Java对象头里面，

![image](https://s2.loli.net/2022/05/05/pCuxJ9d8oBSiUhQ.png)

具体位置是对象头里面的**MarkWord**，MarkWord里默认数据是存储对象的HashCode等信息，

![image](https://s2.loli.net/2022/05/05/xIHYrCjzqnQlwpO.png)

但是会随着对象的运行改变而发生变化，不同的锁状态对应着不同的记录存储方式

![image](https://s2.loli.net/2022/05/05/rwPvZ3jRbTO9nhx.png)

### 了解各种锁

#### 自旋锁

##### 原理

自旋锁原理非常简单，如果持有锁的线程能在很短时间内释放锁资源，那么那些等待竞争锁的线程就不需要做内核态和用户态之间的切换进入阻塞挂起状态，它们只需要等一等（自旋），等持有锁的线程释放锁后即可立即获取锁，这样就避免用户线程和内核的切换的消耗。

但是线程自旋是需要消耗CPU的，说白了就是让CPU在做无用功，线程不能一直占用CPU自旋做无用功，所以需要设定一个自旋等待的最大时间。

如果持有锁的线程执行的时间超过自旋等待的最大时间扔没有释放锁，就会导致其它争用锁的线程在最大等待时间内还是获取不到锁，这时争用线程会停止自旋进入阻塞状态。

##### 自旋锁的优缺点

自旋锁尽可能的减少线程的阻塞，这对于锁的竞争不激烈，且占用锁时间非常短的代码块来说性能能大幅度的提升，因为自旋的消耗会小于线程阻塞挂起操作的消耗！

但是如果锁的竞争激烈，或者持有锁的线程需要长时间占用锁执行同步块，这时候就不适合使用自旋锁了，因为自旋锁在获取锁前一直都是占用cpu做无用功，占着XX不XX，线程自旋的消耗大于线程阻塞挂起操作的消耗，其它需要cup的线程又不能获取到cpu，造成cpu的浪费。

##### 自旋锁的时间阈值

自旋锁的目的是为了占着CPU的资源不释放，等到获取到锁立即进行处理。但是如何去选择自旋的执行时间呢？如果自旋执行时间太长，会有大量的线程处于自旋状态占用CPU资源，进而会影响整体系统的性能。因此自旋次数很重要

JVM对于自旋次数的选择，jdk1.5默认为**10**次，在1.6引入了**适应性自旋锁**，适应性自旋锁意味着自旋的时间不在是固定的了，而是由前一次在同一个锁上的自旋时间以及锁的拥有者的状态来决定，基本认为一个线程上下文切换的时间是最佳的一个时间。

JDK1.6中-XX:+UseSpinning开启自旋锁； JDK1.7后，去掉此参数，由jvm控制；

#### 锁的状态

一共有四种状态，**无锁状态**，**偏向锁状态**，**轻量级锁状态**和**重量级锁状态**，它会随着竞争情况逐渐升级。锁可以升级但不能降级，目的是为了提高获得锁和释放锁的效率。

##### 偏向锁

**减少同一线程获取锁的代价（CAS）**

大多数情况下，锁不存在多线程竞争，总是由同一线程多次获得

核心思想：

如果一个线程获得了锁，那么锁就进入了偏向模式，此时**Mark Word**的结构也变成了锁偏向锁结构，当该线程再次请求锁时，无需再做任何同步操作，即获取锁的过程只需要检查Mark Word的锁标记位为偏向锁以及当前线程id等于Mark Word的**Thread ID**即可，这样就省去了大量有关锁申请的操作。

**适用场景:不适用于锁竞争比较激烈的多线程场合。**

##### 轻量级锁

轻量级锁是由偏向锁升级来的，偏向锁运行在一个线程进入同步块的情况下，当第二个线程加入锁争用的时候，偏向锁就会升级为轻量级锁。

**适用场景：线程交替执行代码块**

**若存在同一时间访问同一锁的情况，就会导致轻量级锁膨胀为重量级锁。**

##### 不同锁的比较

![image](https://s2.loli.net/2022/05/05/6tHOPpdAerDFVX9.png)

### synchronized和Lock的区别

1. synchronized 内置的Java**关键字**，Lock是一个Java类。
2. synchronized 无法判断获取锁的状态，Lock可以判断是否获取到了锁
3. synchronized 会自动释放锁，Lock必须**手动**释放锁，如果不释放锁，**死锁**
4. synchronized 线程1（获得锁，阻塞）、线程2（等待，傻傻地等）；Lock锁就不一定会等待下去。
5. synchronized 托管给jvm执行，原始采用的是CPU**悲观锁**机制；Lock采用的是**乐观锁**方式
6. 锁机制不同，synchronized 操作**Mark World**，Lock调用**UnSafe**的***park***()
7. synchronized **非公平锁**；Lock可以做成**公平锁**和非公平锁（**构造方法**）

## 常见考题

### 1.sychronied修饰普通方法和静态方法的区别？

对象锁是用于对象实例方法，或者一个对象实例上的，类锁是用于类的静态方法或者一个类的class对象上的。我们知道，类的对象实例可以有很多个，但是每个类只有一个class对象，所以不同对象实例的对象锁是互不干扰的，但是每个类只有一个类锁。

但是有一点必须注意的是，其实类锁只是一个概念上的东西，并不是真实存在的，类锁其实锁的是每个类的对应的class对象。类锁和对象锁之间也是互不干扰的。



### 2.什么是可见性？

**可见性是指当多个线程访问同一个变量时，一个线程修改了这个变量的值，其他线程能够立即看得到修改的值。**

由于线程对变量的所有操作都必须在工作内存中进行，而不能直接读写主内存中的变量，那么对于共享变量V，它们首先是在自己的工作内存，之后再同步到主内存。可是并不会及时的刷到主存中，而是会有一定时间差。很明显，这个时候线程 A 对变量 V 的操作对于线程 B 而言就不具备可见性了 。

要解决共享对象可见性这个问题，我们可以使用volatile关键字或者是加锁。



### 3.锁分哪几类？

![image](https://s2.loli.net/2022/05/05/FBPo1ESi25TzfNe.png)

### 4.CAS无锁编程的原理

使用当前的处理器基本都支持CAS()的指令，只不过每个厂家所实现的算法并不一样，每一个CAS操作过程都包含三个运算符：一个内存地址V，一个期望的值A和一个新值B，操作的时候如果这个地址上存放的值等于这个期望的值A，则将地址上的值赋为新值B，否则不做任何操作。

CAS的基本思路就是，如果这个地址上的值和期望的值相等，则给其赋予新值，否则不做任何事儿，但是要返回原值是多少。循环CAS就是在一个循环里不断的做cas操作，直到成功为止。

还可以说说CAS的三大问题。ABA,开销问题，只能保证一个共享变量的原子操作。

### 5.ReentrantLock的实现原理。

线程可以**重复进入**任何一个它已经拥有的锁所同步着的代码块，synchronized、ReentrantLock都是可重入的锁。在实现上，就是线程每次获取锁时判定如果获得锁的线程是它自己时，简单将计数器累积即可，每 释放一次锁，进行计数器累减，直到计算器归零，表示线程已经彻底释放锁。

底层则是利用了JUC中的**AQS**来实现的。

### 6.AQS原理

**是用来构建锁或者其他同步组件的基础框架**，比如**ReentrantLock**、**ReentrantReadWriteLock**和**CountDownLatch**就是基于AQS实现的。它使用了一个int成员变量表示同步状态，通过内置的**FIFO**队列来完成资源获取线程的排队工作。它是**CLH**队列锁的一种变体实现。它可以实现2种同步方式：独占式，共享式。

AQS的主要使用方式是**继承**，子类通过继承AQS并实现它的抽象方法来管理同步状态，同步器的设计基于**模板方法模式**，所以如果要实现我们自己的同步工具类就需要覆盖其中几个可重写的方法，如**tryAcquire**、**tryReleaseShared**等等。

这样设计的目的是同步组件（比如锁）是面向使用者的，它定义了使用者与同步组件交互的接口（比如可以允许两个线程并行访问），隐藏了实现细节；同步器面向的是锁的实现者，它简化了锁的实现方式，屏蔽了同步状态管理、线程的排队、等待与唤醒等底层操作。这样就很好地隔离了使用者和实现者所需关注的领域。

在内部，AQS维护一个共享资源**state**，通过内置的FIFO来完成获取资源线程的排队工作。该队列由一个一个的Node结点组成，每个Node结点维护一个prev引用和next引用，分别指向自己的前驱和后继结点，构成一个双端双向链表。



### 7.Synchronized的原理

synchronized (this)原理：涉及两条指令：**monitorenter**，**monitorexit**；再说同步方法，从同步方法反编译的结果来看，方法的同步并没有通过指令monitorenter和monitorexit来实现，相对于普通方法，其常量池中多了***ACC_SYNCHRONIZED***标示符。

JVM就是根据该标示符来实现方法的同步的：当方法被调用时，调用指令将会检查方法的 ***ACC_SYNCHRONIZED*** 访问标志是否被设置，如果设置了，执行线程将先获取monitor，获取成功之后才能执行方法体，方法执行完后再释放monitor。在方法执行期间，其他任何线程都无法再获得同一个monitor对象。



### 8.Synchronized以及与ReentrantLock的区别



### 9.Synchronized做了哪些优化？

引入如**自旋锁**、**适应性自旋锁**、**锁消除**、**锁粗化**、**偏向锁**、**轻量级锁**、**逃逸分析**

等技术来减少锁操作的开销。

### 10.Synchronized static与非static锁的区别和范围



### 11.volatile 能否保证线程安全？在DCL上的作用是什么？

不能保证，在DCL的作用是：volatile是会保证被修饰的变量的**可见性**和 **有序性**，保证了单例模式下，保证在创建对象的时候的执行顺序一定是

> 1.分配内存空间
>
> 2.实例化对象instance
>
> 3.把instance引用指向已分配的内存空间,此时instance有了内存地址,不再为null了

的步骤, 从而保证了instance要么为null 要么是已经完全初始化好的对象。

### 12.volatile和synchronize有什么区别？

**volatile**是**最轻量的同步机制**。

volatile保证了不同线程对这个变量进行操作时的**可见性**，即一个线程修改了某个变量的值，这新值对其他线程来说是立即可见的。但是volatile**不能保证操作的原子性**，因此多线程下的写复合操作会导致线程安全问题。

关键字synchronized可以修饰方法或者以同步块的形式来进行使用，它主要确保多个线程在同一个时刻，只能有一个线程处于方法或者同步块中，它保证了线程对变量访问的**可见性和排他性**，又称为**内置锁机制**。

### 13.什么是守护线程？你是如何退出一个线程的？

**Daemon**（守护）线程是一种支持型线程，因为它主要被用作程序中后台调度以及支持性工作。这意味着，当一个Java虚拟机中不存在**非**Daemon线程的时候，Java虚拟机将会退出。可以通过调用***Thread.setDaemon(true)***将线程设置为Daemon线程。我们一般用不上，比如垃圾回收线程就是Daemon线程。

**线程的中止：**

要么是run执行完成了，要么是抛出了一个未处理的异常导致线程提前结束。

暂停、恢复和停止操作对应在线程Thread的API就是***suspend()***、***resume()***和***stop()***。但是这些API是过期的，也就是不建议使用的。因为会导致程序可能工作在不确定状态下。

安全的中止则是其他线程通过调用某个线程A的***interrupt()***方法对其进行中断操作，被中断的线程则是通过线程通过方法i***sInterrupted()***来进行判断是否被中断，也可以调用静态方法Thread.interrupted()来进行判断当前线程是否被中断，不过Thread.interrupted()会同时将中断标识位改写为false。

### 14.sleep 、wait、yield 的区别，wait 的线程如何唤醒它？

yield()方法：使当前线程让出CPU占有权，但让出的时间是不可设定的。也不会释放锁资源。所有执行yield()的线程有可能在进入到就绪状态后会被操作系统再次选中马上又被执行。

yield() 、sleep()被调用后，都不会释放当前线程所持有的锁。

调用wait()方法后，会释放当前线程持有的锁，而且当前被唤醒后，会重新去竞争锁，锁竞争到后才会执行wait方法后面的代码。

Wait通常被用于线程间交互，sleep通常被用于暂停执行，yield()方法使当前线程让出CPU占有权。

wait 的线程使用notify/notifyAll()进行唤醒。

### 15.sleep是可中断的么？

sleep本身就支持中断，如果线程在sleep期间被中断，则会抛出一个中断异常。

### 16.线程生命周期



### 17.ThreadLocal是什么？

ThreadLocal是Java里一种特殊的变量。ThreadLocal为每个线程都提供了变量的副本，使得每个线程在某一时间訪问到的并非同一个对象，这样就隔离了多个线程对数据的数据共享。

在内部实现上，每个线程内部都有一个**ThreadLocalMap**，用来保存每个线程所拥有的变量副本。

### 18.线程池基本原理

在开发过程中，合理地使用线程池能够带来3个好处。

第一：**降低资源消耗**。第二：**提高响应速度**。第三：**提高线程的可管理性**。

1.	如果当前运行的线程少于corePoolSize，则创建新线程来执行任务（注意，执行这一步骤需要获取全局锁）。
1.	如果运行的线程等于或多于corePoolSize，则将任务加入BlockingQueue。
1.	如果无法将任务加入BlockingQueue（队列已满），则创建新的线程来处理任务。
1.	如果创建新线程将使当前运行的线程超出maximumPoolSize，任务将被拒绝，并调用RejectedExecutionHandler.rejectedExecution()方法。

### 19.有三个线程T1，T2，T3，怎么确保它们按顺序执行？

可以用join方法实现。