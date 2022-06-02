---
title: Android Framework Binder 总结
date: 2022-06-02 10:07:22
tags:
  - Android
  - FrameWork
  - Binder
---

# Android Framework Binder 总结



### Binder系列传送门

[Android Framework Binder 总结](https://juejin.cn/post/7104338528439369758)

[Binder源码解析（一）](https://juejin.cn/post/7104343457610596360/)

[Binder源码解析（二）](https://juejin.cn/post/7104340048920707080)





## 一，Binder的定义

|                         | 定义                                                         | 作用                                            |
| ----------------------- | ------------------------------------------------------------ | ----------------------------------------------- |
| 从机制、模型角度        | Binder是一种Android的实现跨进程通信（IPC）的方式（即**Binder机制**模型） | 在Android中实现跨进程通信                       |
| 从模型的结构、组成角度  | Binder是一种虚拟的物理设备驱动（即**Binder驱动**）           | 连接Service、Client和Service Manager进程        |
| 从Android代码的实现角度 | Binder是一个类，实现了IBinder接口（即**Binder**类）          | 将Binder机制模型以代码的形式具体是现在Android中 |


<!--more-->




## 二，Binder与传统IPC对比

|        | Binder                               | 共享内存                                 |                       Socket                        |
| ------ | ------------------------------------ | ---------------------------------------- | :-------------------------------------------------: |
| 性能   | 需要拷贝一次                         | 无需拷贝                                 |                    需要拷贝两次                     |
| 特点   | 基于C/S架构，易用性高                | 控制复杂，易用性差                       | 基于C/S架构，作为一款通用接口，其传输效率低，开销大 |
| 安全性 | 为每个App分配UID，同时支持实名和匿名 | 依赖上层协议，访问接入点是开发的，不安全 |      依赖上层协议，访问接入点是开发的，不安全       |





## 三，Linux下传统的进程间通信原理

### 3.1 内存划分

用户空间是用户程序代码运行的地方，内核空间是内核代码运行的地方。为了安全，它们是隔离的，即使用户的程序崩溃了，内核也不受影响。

![内存划分](https://s2.loli.net/2022/06/01/z7u2HvPi6Jbfsqt.png)



- 进程隔离

  > 为了保证 安全性 & 独立性，一个进程 不能直接操作或者访问另一个进程，即`Android`的进程是**相互独立、隔离的**



- 32位系统，即2^32，即总共可访问地址为4G。内核空间为1G，用户空间为3G。

![image-20220601110138025](https://s2.loli.net/2022/06/01/cnH5hPOqzG6BWpI.png)

- 64位系统，低位：0～47位才是有效的可变地址（寻址空间256T），高位：48～63位全补0或全补1。一般高位全补0对应的地址空间是用户空间。高位全补1对应的是内核空间



### 3.2 传统IPC传输数据

![image-20220601110312050](https://s2.loli.net/2022/06/01/7eWM8f3nqY9FLQJ.png)



### 3.3 Binder传输数据

![image-20220601110407509](https://s2.loli.net/2022/06/01/yZWHGCdIABfRwpT.png)



**工作流程**

> 1. Binder驱动，创建一块接收缓存区。
> 2. 实现地址映射关系：即根据需映射的接收进程信息，实现**内核缓存区**和**接收进程用户空间地址**同时映射到**同一个接收缓存区**中。
> 3. 发送进程通过系统调用 **copy_from_user()** 发送数据到虚拟内存区域（数据拷贝一次）
> 4. 由于**内核缓存区**和**接收进程的用户地址空间**存在映射关系（同时映射Binder创建的接收缓存区中），故相当于也发送到了接收进程的用户空间地址，即实现跨进程通信。



### 3.4  mmap

Linux通过将一个虚拟内存区域与一个磁盘上的对象关联起来，以初始化这个虚拟内存区域的内容，这个过程称为**内存映射(memory mapping)**。

![mmap](https://s2.loli.net/2022/06/01/1uZgmiGjLNfvawF.png)



- 对文件进行mmap，会在进程的虚拟内存分配地址空间，创建映射关系
- 实现这样的映射关系后，就可以采用指针的方式读写操作这一段内存，而系统会自动回写到对应的文件磁盘上





## 四，Binder通信模型

图片引用自[这里](https://blog.csdn.net/carson_ho/article/details/73560642?ops_request_misc=%257B%2522request%255Fid%2522%253A%2522165405141016781432931945%2522%252C%2522scm%2522%253A%252220140713.130102334.pc%255Fall.%2522%257D&request_id=165405141016781432931945&biz_id=0&utm_medium=distribute.pc_search_result.none-task-blog-2~all~first_rank_ecpm_v1~hot_rank-2-73560642-null-null.142^v11^pc_search_result_control_group,157^v12^control&utm_term=binder%E9%A9%B1%E5%8A%A8&spm=1018.2226.3001.4187)

![eaed46dda99cc654ec04d80dfd694b0f](https://s2.loli.net/2022/06/01/4tmfwRci7NYSk5q.png)





### 角色说明

- 用户进程：使用服务的进程
- 服务进程：提供服务的进程
- Service Manager进程：管理服务的注册和查询
- Binder驱动：一种虚拟设备驱动，可以连接用户和服务，ServiceManager进程。

### 步骤说明

- 注册服务
  - 服务进程向Binder进程发起服务注册
  - Binder驱动将注册请求转发给ServiceManager进程
  - ServiceManager进程添加这个服务进程

- 获取服务
  - 用户进程向Binder驱动发起获取服务的请求，传递要获取的服务名称
  - Binder驱动将该请求转发给ServiceManager进程
  - ServiceManager进程查到到用户进程需要的服务进程信息
  - 最后通过Binder驱动将上述服务信息返回个用户进程

- 使用服务
  - Binder驱动为跨进程通信准备：实现内存映射
  - 用户进程将参数数据发送到服务进程
  - 服务进程根据用户进程要求调用目标方法
  - 服务进程将目标方法的结果返回给用户进程



## 五，Binder源码图解

#### Binder框架图解

![awzs4-h37yc](https://s2.loli.net/2022/06/01/thDELl72XFzmOyg.png)



#### Binder设计的类

![aa0ql-g6wra](https://s2.loli.net/2022/06/01/v5fWum9XJ8CLVQT.png)



#### Binder驱动

![azkr4-lo9gu](https://s2.loli.net/2022/06/01/GMblChqHmSgWV8T.png)



![20180606160806774](https://s2.loli.net/2022/06/02/pnQhR9GX6v8HtfL.jpg)





## 六，Binder源码解析



[Binder源码解析（一）](https://juejin.cn/post/7104343457610596360/)

[Binder源码解析（二）](https://juejin.cn/post/7104340048920707080)



## 七，AIDL

AIDL (Android Interface Definition Language) 是一种接口定义语言，用于生成可以 在Android设备上两个进程之间进行进程间通信(`Interprocess` `Communication`, `IPC`) 的代码。如果在一个进程中（例如Activity）要调用另一个进程中（例如Service） 对象的操作，就可以使用AIDL生成可序列化的参数，来完成进程间通信。简言之，AIDL能够实现进程间通信，其内部是通过Binder机制来实现的。



AIDL的使用实质就是对Binder机制的封装，主要就是将Binder封装成一个代理对象proxy，从用户的角度看，就像是客户端直接调用了服务端的代码。

> 1. 创建 AIDL
>    1. 创建要操作的实体类，实现 Parcelable 接口，以便序列化/反序列化
>    2. 新建 aidl 文件夹，在其中创建接口 aidl 文件以及实体类的映射 aidl 文件
>    3. Make project ，生成 Binder 的 Java 文件
> 2. 服务端
>    1. 创建 Service，在其中创建上面生成的 Binder 对象实例，实现接口定义的方法
>    2. 在 onBind() 中返回
> 3. 客户端
>    1. 实现 ServiceConnection 接口，在其中拿到 AIDL 类
>    2. bindService()
>    3. 调用 AIDL 类中定义好的操作请求
>       

![微信图片_20220602021531](https://s2.loli.net/2022/06/02/8nGjYpS2AaeFMs3.png)



## 八，Binder常见问题

### 1. Binder机制是如何跨进程的

由于发送方进程1和接收方进程2不能直接进行通信，由于内核空间是共享的，发送方通过copy_from_user()把数据直接拷贝到内核空间，因为内核空间与接收方的用户空间同时映射到一块物理内存中，所以说数据通过copy_from_user()拷贝到内核地址空间指定的虚拟内存后，相对于直接进入了接收方的用户空间，所以整个通信过程只进行了一次内存拷贝，这个映射就是通过mmap实现的。

### 2. 为什么Intent不能传递大数据

限制大小： **1M - 8K**
实际传递过程中比（1M - 8K）还要小些，数据还需要打包
就好像网络通信过程中数据会有包头、命令等

如果在异步情况下，限制大小： （1M - 8K）/ 2



### 3. Binder 的线程管理

每个 Binder 的 Server 进程会创建很多线程来处理 Binder 请求，可以简单的理解为创建了一个 Binder 的线程池吧，而真正管理这些线程并不是由这个 Server 端来管理的，而是由 Binder 驱动进行管理的。

一个进程的 Binder 线程数默认最大是 16，超过的请求会被阻塞等待空闲的 Binder 线程。


### 



