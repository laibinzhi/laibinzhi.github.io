---
title: Android系统启动流程
date: 2022-06-02 19:22:54
tags:
  - Android
  - FrameWork
---



# Android系统启动流程

## 一，序言

Android是谷歌开发的一款基于Linux的开源操作系统，下图所示为 Android 平台的主要组件

![android-stack](https://s2.loli.net/2022/06/02/1JjIc3UQdMg2oBD.png)



### Linux 内核

Android 平台的基础是 Linux 内核。例如，Android Runtime (ART) 依靠 Linux 内核来执行底层功能，例如线程和低层内存管理。

使用 Linux 内核可让 Android 利用主要安全功能，并且允许设备制造商为著名的内核开发硬件驱动程序。


<!--more-->



### 硬件抽象层 (HAL)

硬件抽象层 (HAL) 提供标准界面，向更高级别的 Java API 框架显示设备硬件功能。HAL 包含多个

库模块，其中每个模块都为特定类型的硬件组件实现一个界面，例如相机或蓝牙模块。当框架 API

要求访问设备硬件时，Android 系统将为该硬件组件加载库模块。

### Android Runtime

对于运行 Android 5.0（API 级别 21）或更高版本的设备，每个应用都在其自己的进程中运行，并

且有其自己的 Android Runtime (ART) 实例。ART 编写为通过执行 DEX 文件在低内存设备上运行

多个虚拟机，DEX 文件是一种专为 Android 设计的字节码格式，经过优化，使用的内存很少。编

译工具链（例如 Jack）将 Java 源代码编译为 DEX 字节码，使其可在 Android 平台上运行。

> ART 的部分主要功能包括：
>
> - 预先 (AOT) 和即时 (JIT) 编译
> - 优化的垃圾回收 (GC)
> - 在 Android 9（API 级别 28）及更高版本的系统中，支持将应用软件包中的 Dalvik Executable 格 式 (DEX) 文件转换为更紧凑的机器代码。
> - 更好的调试支持，包括专用采样分析器、详细的诊断异常和崩溃报告，并且能够设置观察点以监控特定字段。在 Android 版本 5.0（API 级别 21）之前，Dalvik 是 Android Runtime。如果您的应用在 ART 上运行效果很好，那么它应该也可在 Dalvik 上运行，但反过来不一定。

Android 还包含一套核心运行时库，可提供 Java API 框架所使用的 Java 编程语言中的大部分功能，包括一些 Java 8 语言功能。

### 原生 C/C++ 库

许多核心 Android 系统组件和服务（例如 ART 和 HAL）构建自原生代码，需要以 C 和 C++ 编写的原生库。Android 平台提供 Java 框架 API 以向应用显示其中部分原生库的功能。例如，您可以通过 Android 框架的 Java OpenGL API 访问 OpenGL ES，以支持在应用中绘制和操作 2D 和 3D 图形。如果开发的是需要 C 或 C++ 代码的应用，可以使用 Android NDK 直接从原生代码访问某些原生平台库。

### Java API 框架

您可通过以 Java 语言编写的 API 使用 Android OS 的整个功能集。这些 API 形成创建 Android 应

用所需的构建块，它们可简化核心模块化系统组件和服务的重复使用，包括以下组件和服务：

- 丰富、可扩展的视图系统，可用以构建应用的 UI，包括列表、网格、文本框、按钮甚至可嵌入的网络浏览器
- 资源管理器，用于访问非代码资源，例如本地化的字符串、图形和布局文件
- 通知管理器，可让所有应用在状态栏中显示自定义提醒
- Activity 管理器，用于管理应用的生命周期，提供常见的导航返回栈
- 内容提供程序，可让应用访问其他应用（例如“联系人”应用）中的数据或者共享其自己的数据。开发者可以完全访问 Android 系统应用使用的框架 API。 

### 系统应用

- Android 随附一套用于电子邮件、短信、日历、互联网浏览和联系人等的核心应用。平台随附的应用与用户可以选择安装的应用一样，没有特殊状态。因此第三方应用可成为用户的默认网络浏览器、短信 Messenger 甚至默认键盘（有一些例外，例如系统的“设置”应用）。

- 系统应用可用作用户的应用，以及提供开发者可从其自己的应用访问的主要功能。例如，如果您的应用要发短信，您无需自己构建该功能，可以改为调用已安装的短信应用向您指定的接收者发送消息。



## 二，Android系统启动流程

参考http://gityuan.com/2016/02/01/android-booting/

![android-boot](https://s2.loli.net/2022/06/02/gGAvIiKpl62Lmnx.jpg)



![Android framework](https://s2.loli.net/2022/06/02/yF4xdUMlZKePvtq.png)

![Android系统启动](https://s2.loli.net/2022/06/02/hK7NBD1syTWURr5.png)

### 1. 启动电源以及系统启动

当电源按下，引导芯片代码开始从预定义的地方（固化在ROM）开始执行。加载引导程序到RAM，然后执行

### 2. 引导程序

引导程序是在Android操作系统开始运行前的一个小程序。引导程序是运行的第一个程序，因此它是针对特定的主板与芯片的。设备制造商要么使用很受欢迎的引导程序比如redboot、uboot、qi

bootloader或者开发自己的引导程序，它不是Android操作系统的一部分。引导程序是OEM厂商或者运营商加锁和限制的地方。

引导程序分两个阶段执行。

> 1. 第一个阶段，检测外部的RAM以及加载对第二阶段有用的程序；
>
> 2. 第二阶段，引导程序设置网络、内存等等。这些对于运行内核是必要的，为了达到特殊的目标，引导程序可以根据配置参数或者输入数据设置内核。

Android引导程序可以在\bootable\bootloader\legacy\usbloader找到。传统的加载器包含两个文件，需要在这里说明：

> 1. init.s初始化堆栈，清零BBS段，调用main.c的_main()函数；
> 1. main.c初始化硬件（闹钟、主板、键盘、控制台），创建linux标签

### 3. 内核

Android内核与桌面linux内核启动的方式差不多。内核启动时，设置缓存、被保护存储器、计划列表，加载驱动。当内核完成系统设置，它首先在系统文件中寻找”init”文件，然后启动root进程或者系统的第一个进程

### 4. init进程

init进程是Linux系统中用户空间的第一个进程，进程号固定为1。Kernel启动后，在用户空间启动init进程，并调用init中的main()方法执行init进程的职责。



### 5. 启动Lancher App





## 三，源码分析

### init进程分析

参考http://gityuan.com/2016/02/05/android-init/

其中init进程是Android系统中及其重要的第一个进程，接下来我们来看下init进程注意做了些什么

1. 创建和挂载启动所需要的文件目录
2. 初始化和启动属性服务
3. 解析**init.rc**配置文件并启动**Zygote**进程

![android-booting](https://s2.loli.net/2022/06/02/pPk5ZOM9HEI2UBF.jpg)



### zygote进程

参考http://gityuan.com/2016/02/13/android-zygote/

Zygote中文翻译为“受精卵”，正如其名，它主要用于孵化子进程。在Android系统中有以下两种程序：java应用程序，主要基于ART虚拟机，所有的应用程序apk都属于这类native程序，也就是利用C或C++语言开发的程序，如bootanimation。所有的Java应用程序进程及系统服务SystemServer进程都由Zygote进程通过Linux的fork()函数孵化出来的，这也就是为什么把它称为Zygote的原因，因为他就像一个受精卵，孵化出无数子进程，而native程序则由Init程序创建启动。Zygote进程最初的名字不是“zygote”而是“app_process”，这个名字是在Android.mk文件中定义的Zgyote是Android中的第一个art虚拟机，他通过socket的方式与其他进程进行通信。这里的“其他进程”其实主要是系统进程——SystemServer

> Zygote是一个C/S模型，Zygote进程作为服务端，它主要负责创建Java虚拟机，加载系统资源，启动SystemServer进程，以及在后续运行过程中启动普通的应用程序，其他进程作为客户端向它发出“孵化”请求，而Zygote接收到这个请求后就“孵化”出一个新的进程。比如，当点击Launcher里的应用程序图标去启动一个新的应用程序进程时，这个请求会到达框架层的核心服务ActivityManagerService中，当AMS收到这个请求后，它通过调用Process类发出一个“孵化”子进程的Socket请求，而Zygote监听到这个请求后就立刻fork一个新的进程出来



Zygote启动过程的调用流程图：

![zygote_start](https://s2.loli.net/2022/06/02/DlULzki5SvoMybV.jpg)

1. 解析init.zygote.rc中的参数，创建AppRuntime并调用AppRuntime.start()方法；
2. 调用AndroidRuntime的startVM()方法创建虚拟机，再调用startReg()注册JNI函数；
3. 通过JNI方式调用ZygoteInit.main()，第一次进入Java世界；
4. registerZygoteSocket()建立socket通道，zygote作为通信的服务端，用于响应客户端请求；
5. preload()预加载通用类、drawable和color资源、openGL以及共享库以及WebView，用于提高app启动效率；
6. zygote完毕大部分工作，接下来再通过startSystemServer()，fork得力帮手system_server进程，也是上层framework的运行载体。
7. zygote功成身退，调用runSelectLoop()，随时待命，当接收到请求创建新进程请求时立即唤醒并执行相应工作。



### System Server启动流程

System Server 是Zygote fork 的第一个Java 进程， 这个进程非常重要，因为他们有很多的系统线程，提供所有核心的系统服务看到大名鼎鼎的WindowManager, ActivityManager了吗？对了，它们都是运行在system_server的进程里。还有很多“Binder-x”的线程，它们是各个Service为了响应应用程序远程调用请求而创建的。除此之外，还有很多内部的线程，比如 ”UI thread”, “InputReader”, “InputDispatch” 等等，我，现在我们只关心System Server是如何创建起来的。

**SystemServer的main()** 函数。

```java
public static void main(String[] args) { 
  new SystemServer().run();
} 
```

记下来分成4部分详细分析SystemServer run方法的初始化流程：

初始化必要的SystemServer环境参数，比如系统时间、默认时区、语言、load一些Library等等，

初始化Looper，我们在主线程中使用到的looper就是在SystemServer中进行初始化的

初始化Context，只有初始化一个Context才能进行启动Service等操作，这里看一下源码：

```java
private void createSystemContext() {
  ActivityThread activityThread = ActivityThread.systemMain(); 
  mSystemContext = activityThread.getSystemContext();
  mSystemContext.setTheme(DEFAULT_SYSTEM_THEME); 
  final Context systemUiContext = activityThread.getSystemUiContext();
  systemUiContext.setTheme(DEFAULT_SYSTEM_THEME);
}
```

看到没有ActivityThread就是这个时候生成的

继续看ActivityThread中如何生成Context： 

```java
public ContextImpl getSystemContext() {
  synchronized (this) { 
    if (mSystemContext == null) { 
      mSystemContext = ContextImpl.createSystemContext(this); 
    }return mSystemContext; 
  } 
}
```

ContextImpl是Context类的具体实现，里面封装完成了生成几种常用的createContext的方法：

```java
static ContextImpl createSystemContext(ActivityThread mainThread) {
  LoadedApk packageInfo = new LoadedApk(mainThread); 
  //省略代码 
  return context; 
}

static ContextImpl createSystemUiContext(ContextImpl systemContext) { 
  final LoadedApk packageInfo = systemContext.mPackageInfo; 
  //省略代码
  return context; 
}

static ContextImpl createAppContext(ActivityThread mainThread, LoadedApk packageInfo) {
  if (packageInfo == null) throw new IllegalArgumentException("packageInfo"); //省略代码 
  return context; 
}

static ContextImpl createActivityContext(ActivityThread mainThread, LoadedApk packageInfo, ActivityInfo activityInfo, IBinder activityToken, int displayId, Configuration overrideConfiguration) { 
  //省略代码 
  return context; 
}
```

初始化SystemServiceManager,用来管理启动service，SystemServiceManager中封装了启动Service的startService方法启动系统必要的Service，启动service的流程又分成三步走：

```java
// Start services. 
try {
  traceBeginAndSlog("StartServices"); 
  startBootstrapServices(); 
  startCoreServices(); 
  startOtherServices(); 
  SystemServerInitThreadPool.shutdown(); 
} catch (Throwable ex) { 
  // 
} finally { 
  traceEnd();
}
```

启动BootstrapServices,就是系统必须需要的服务，这些服务直接耦合性很高，所以干脆就放在一个方法里面一起启动，比如PowerManagerService、RecoverySystemService、DisplayManagerService、ActivityManagerService等等启动以基本的核心Service，很简单，只有三个BatteryService、UsageStatsService、WebViewUpdateService启动其它需要用到的Service，比如NetworkScoreService、AlarmManagerService



Zygote会默默的在后台观看像Sytem Server，一旦发现System Server 挂掉了，将其回收，然后将自己杀掉，重新开始新的一生。代码在dalvik/vm/native/dalvik_system_zygote.cpp 中

```c++
static void Dalvik_dalvik_system_Zygote_forkSystemServer( const u4* args, JValue* pResult){ 
  ... 
    pid_t pid; pid = forkAndSpecializeCommon(args, true);
  ... 
    if (pid > 0) { 
      int status; 
      gDvm.systemServerPid = pid;
      /* WNOHANG 会让waitpid 立即返回，这里只是为了预防上面的赋值语句没有完成之 前SystemServer就crash 了*/ 
      if (waitpid(pid, &status, WNOHANG) == pid) {
        ALOGE("System server process %d has died. Restarting Zygote!", pid); 
        kill(getpid(), SIGKILL); 
      }
    }
  RETURN_INT(pid); 
}
/* 真正的处理在这里 */ 
static void sigchldHandler(int s){ 
  ... 
    pid_t pid;
  int status;
  ... 
    while ((pid = waitpid(-1, &status, WNOHANG)) > 0) {
      ...
        if (pid == gDvm.systemServerPid) { 
          ... 
            kill(getpid(), SIGKILL); 
        } 
    }
  ... 
}

static void Dalvik_dalvik_system_Zygote_fork(const u4* args, JValue* pResult){
  pid_t pid; 
  ... 
    setSignalHandler(); //signalHandler 在这里注册 
  ... 
    pid = fork(); 
  ... 
    RETURN_INT(pid);
}
```

在Unix-like系统，父进程必须用 waitpid 等待子进程的退出，否则子进程将变成”Zombie” (僵尸）进程，不仅系统资源泄漏，而且系统将崩溃（没有system server，所有Android应用程序都无法运行）。但是waitpid() 是一个阻塞函数（WNOHANG参数除外)，所以通常做法是在signal 处理数里进行无阻塞的处理，因为每个子进程退出的时候，系统会发出 SIGCHID 信号。Zygote会把自己杀掉， 那父亲死了，所有的应用程序不就成为孤儿了？ 不会，因为父进程被杀掉后系统会自动给所有的子进程发生SIGHUP信号，该信号的默认处理就是将杀掉自己退出当前进程。但是一些后台进程（Daemon)可以通过设置SIG_IGN参数来忽略这个信号，从而得以在后台继续运行。



总结

1. init 根据init.rc 运行 app_process, 并携带‘–zygote’ 和 ’–startSystemServer’ 参数。
1. AndroidRuntime.cpp::start() 里将启动JavaVM，并且注册所有framework相关的系统JNI接口。
1. 第一次进入Java世界，运行ZygoteInit.java::main() 函数初始化Zygote. Zygote 并创建Socket的server 端
1. 然后fork一个新的进程并在新进程里初始化SystemServer. Fork之前，Zygote是preload常用的Java类库，以及系统的resources，同时GC（）清理内存空间，为子进程省去重复的工作。
1. SystemServer 里将所有的系统Service初始化，包括ActivityManager 和 WindowManager, 他们是应用程序运行起来的前提。
1.  依次同时，Zygote监听服务端Socket，等待新的应用启动请求。
1. ActivityManager ready 之后寻找系统的“Startup” Application, 将请求发给Zygote。 
1. Zygote收到请求后，fork出一个新的进程。
1. Zygote监听并处理SystemServer 的 SIGCHID 信号，一旦System Server崩溃，立即将自己杀死。init会重启Zygote.



## 四，总结

### 1. 手机开机andorid系统启动的流程

**当按电源键触发开机，首先会从 ROM 中预定义的地方加载引导程序 BootLoader 到 RAM 中，并执行 BootLoader 程序启动 Linux Kernel， 然后启动用户级别的第一个进程： init 进程。init 进程会解析init.rc 脚本做一些初始化工作，包括挂载文件系统、创建工作目录以及启动系统服务进程等，其中系统服务进程包括 Zygote、service manager、media 等。在 Zygote 中会进一步去启动 system_server 进程，然后在 system_server 进程中会启动 AMS、WMS、PMS 等服务，等这些服务启动之后，AMS 中就会打开 Launcher 应用的 home Activity，最终就看到了手机的 "桌面"。**



1. 启动电源以及系统启动
 
 > 加载引导程序Bootloader到RAM，然后执行。
 
1. 引导程序BootLoader启动
 
 > 引导程序BootLoader是在Android操作系统开始运行前的一个小程序，它的主要作用是把系统OS拉起来并运行。
 
1. Linux内核启动
 
 > 内核启动时，设置缓存、被保护存储器、计划列表、加载驱动。当内核完成系统设置，它首先在系统文件中寻找init.rc文件，并启动init进程。
 
1. init进程启动
 
 >  init进程是系统空间内的第一个进程，进行初始化和启动属性服务，在main方法中进行，包括初始化资源文件和启动一系列的属性服务。通过执行init.rc文件的脚本文件来启动Zygote进程。
 
1. Zygote进程启动
 
 >  所有的应用程序包括system系统进程 都是zygote进程负责创建，因此zygote进程也被称为进程孵化器，它创建进程是通过复制自身来创建应用进程，它在启动过程中会在内部创建一个虚拟机实例，所以通过复制zygote进程而得到的应用进程和系统服务进程都可以快速地在内部的获得一个虚拟机实例拷贝。
 
1. SystemServer进程启动
 
 >  启动Binder线程池和SystemServiceManager，systemServiceManger主要是对系统服务进行创建、启动和生命周期管理，就会启动各种系统服务。（android中最核心的服务AMS就是在SystemServer进程中启动的）
 
1. Launcher启动
 
 >  Launcher组件是由之前启动的systemServer所启动的
 >  这也是andorid系统启动的最后一步，launcher是andorid系统home程序，主要是用来显示系统中已安装的应用程序。    launcher应用程序的启动会通过请求packageManagerService返回系统中已经安装的应用信息，并将这些应用信息通过封装处理成快捷列表显示在系统屏幕上，这样咱们就可以单击启动它们。
 >  被SystemServer进程启动的ActivityManagerService会启动Launcher，Launcher启动后会将已安装应用的快捷图标显示到界面上。



### 2. system_server 为什么要在 Zygote 中启动，而不是由 init 直接启动呢？

Zygote 作为一个孵化器，可以提前加载一些资源，这样 fork() 时基于 Copy-On-Write 机制创建的其他进程就能直接使用这些资源，而不用重新加载。比如 system_server 就可以直接使用 Zygote 中的 JNI函数、共享库、常用的类、以及主题资源。



### 3. 为什么要专门使用 Zygote 进程去孵化应用进程，而不是让 system_server 去孵化呢？

首先 system_server 相比 Zygote 多运行了 AMS、WMS 等服务，这些对一个应用程序来说是不需要的。另外进程的 fork() 对多线程不友好，仅会将发起调用的线程拷贝到子进程，这可能会导致死锁，而system_server 中肯定是有很多线程的。



### 4. 上面具体是怎么导致死锁的吗？

- 在 POSIX 标准中，fork 的行为是这样的：复制整个用户空间的数据（通常使用 copy-on-write 的策略，所以可以实现的速度很快）以及所有系统对象，然后仅复制当前线程到子进程。这里：所有父进程中别的线程，到了子进程中都是突然蒸发掉的

- 对于锁来说，从 OS 看，每个锁有一个所有者，即最后一次 lock 它的线程。假设这么一个环境，在 fork之前，有一个子线程 lock 了某个锁，获得了对锁的所有权。fork 以后，在子进程中，所有的额外线程都人间蒸发了。而锁却被正常复制了，在子进程看来，这个锁没有主人，所以没有任何人可以对它解锁。当子进程想 lock 这个锁时，不再有任何手段可以解开了。程序发生死锁



### 5. Zygote 为什么不采用 Binder 机制进行 IPC 通信？

Binder 机制中存在 Binder 线程池，是多线程的，如果 Zygote 采用 Binder 的话就存在上面说的

fork() 与 多线程的问题了。其实严格来说，Binder 机制不一定要多线程，所谓的 Binder 线程只不过是在循环读取 Binder 驱动的消息而已，只注册一个 Binder 线程也是可以工作的，比如 service manager就是这样的。实际上 Zygote 尽管没有采取 Binder 机制，它也不是单线程的，但它在 fork() 前主动停止了其他线程，fork() 后重新启动了。