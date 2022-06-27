---
title: Android Framework之AMS
date: 2022-06-28 00:59:11
tags:
  - Android
  - FrameWork
  - 源码
---


# Android Framework之AMS



## 一，定义

1. 从java角度来看，ams就是一个java对象，实现了Ibinder接口，所以它是一个用于进程之间通信的接口，这个对象初始化是在systemServer.java 的run()方法里面

   ```java
   public Lifecycle(Context context) { 
       super(context);
       mService = new ActivityManagerService(context); 
   }
   ```


<!--more-->



2.  AMS是一个服务

   >  ActivityManagerService从名字就可以看出，它是一个服务，用来管理Activity，而且是一个系统服务，就是包管理服务，电池管理服务，震动管理服务等。
   >
   > ActivityManagerService是Android系统中一个特别重要的系统服务，也是我们上层APP打交道最多的系统服务之一。ActivityManagerService（以下简称AMS） 主要负责四大组件的启动、切换、调度以及应用进程的管理和调度工作。所有的APP应用都需要与AMS打交道
   >
   > Activity Manager的组成主要分为以下几个部分：
   >
   > 1. 服务代理：由**ActivityManagerProxy**实现，用于与Server端提供的系统服务进行进程间通信
   > 2. 服务中枢：**ActivityManagerNative**继承自Binder并实现**IActivityManager**，它提供了服务接口和Binder接口的相互转化功能，并在内部存储服务代理对像，并提供了**getDefault**方法返回服务代理
   > 3. Client：由ActivityManager封装一部分服务接口供Client调用。ActivityManager内部通过调用**ActivityManagerNative**的**getDefault**方法，可以得到一个**ActivityManagerProxy**对像的引用，进而通过该代理对像调用远程服务的方法
   > 4. Server:由**ActivityManagerService**实现，提供Server端的系统服务

3.  AMS是一个Binder

   > ams实现了Ibinder接口，所以它是一个Binder，这意味着他不但可以用于进程间通信，还是一个线程，因为一个Binder就是一个线程。
   >
   > 如果我们启动一个hello World安卓用于程序，里面不另外启动其他线程，这个里面最少要启动4个线程
   >
   > 1. main线程，只是程序的主线程，也是日常用到的最多的线程，也叫UI线程，因为android的组
   >
   > 件是非线程安全的，所以只允许UI/MAIN线程来操作。
   >
   > 2. GC线程，java有垃圾回收机制，每个java程序都有一个专门负责垃圾回收的线程，
   >
   > 3. Binder1 就是我们的ApplicationThread，这个类实现了Ibinder接口，用于进程之间通信，具体来说，就是我们程序和AMS通信的工具
   >
   > 4. Binder2 就是我们的ViewRoot.W对象，他也是实现了IBinder接口，就是用于我们的应用程序和wms通信的工具。
   >
   >    ```java
   >    public class ActivityManagerService extends IActivityManager.Stub implements Watchdog.Monitor, BatteryStatsImpl.BatteryCallback {}
   >    ```

### 

## 二，ActivityManagerService的启动过程

AMS是在SystemServer中被添加的， 所以先到SystemServer中查看初始化

```java
public static void main(String[] args) {
    new SystemServer().run(); 
}
```

```java
private void run() {
    ...
        createSystemContext(); 
    // Create the system service manager.
    mSystemServiceManager = new SystemServiceManager(mSystemContext);
  mSystemServiceManager.setStartInfo(mRuntimeRestart,mRuntimeStartElapsedTime,mRuntimeStartUptime);
    LocalServices.addService(SystemServiceManager.class, mSystemServiceManager); 
    // Prepare the thread pool for init tasks that can be parallelized
    SystemServerInitThreadPool.get(); 
} 
finally {
    traceEnd();// InitBeforeStartServices 
}// Start services. 
try {
    traceBeginAndSlog("StartServices");
    startBootstrapServices();
    startCoreServices();
    startOtherServices();
    SystemServerInitThreadPool.shutdown();
} catch (Throwable ex) { 
    throw ex; 
} finally {
    traceEnd(); 
}
... 
    // Loop forever. 
    Looper.loop(); 
throw new RuntimeException("Main thread loop unexpectedly exited"); 
}
```

在**SystemServer**中，在startBootstrapServices()中去启动了AMS

```java
private void startBootstrapServices() {
    ...
    // Activity manager runs the show. 
    traceBeginAndSlog("StartActivityManager"); 
    //启动了AMS
    mActivityManagerService = mSystemServiceManager.startService( ActivityManagerService.Lifecycle.class).getService();
    mActivityManagerService.setSystemServiceManager(mSystemServiceManager);
    mActivityManagerService.setInstaller(installer); traceEnd(); 
    ... 
    // Now that the power manager has been started, let the activity manager
    // initialize power management features. 
    traceBeginAndSlog("InitPowerManagement"); 
    mActivityManagerService.initPowerManagement(); 
    traceEnd(); 
    // Set up the Application instance for the system process and get started. 
    traceBeginAndSlog("SetSystemProcess");
    mActivityManagerService.setSystemProcess();
    traceEnd(); 
}
```

AMS是通过SystemServiceManager.startService去启动的，参数是ActivityManagerService.Lifecycle.class， 首先看看startService方法

```java
public <T extends SystemService> T startService(Class<T> serviceClass) {
    try {
        final String name = serviceClass.getName();
        Slog.i(TAG, "Starting " + name);
        Trace.traceBegin(Trace.TRACE_TAG_SYSTEM_SERVER, "StartService " + name);

        // Create the service.
        if (!SystemService.class.isAssignableFrom(serviceClass)) {
            throw new RuntimeException("Failed to create " + name
                    + ": service must extend " + SystemService.class.getName());
        }
        final T service;
        try {
            Constructor<T> constructor = serviceClass.getConstructor(Context.class);
            service = constructor.newInstance(mContext);
        } catch (InstantiationException ex) {
            throw new RuntimeException("Failed to create service " + name
                    + ": service could not be instantiated", ex);
        } catch (IllegalAccessException ex) {
            throw new RuntimeException("Failed to create service " + name
                    + ": service must have a public constructor with a Context argument", ex);
        } catch (NoSuchMethodException ex) {
            throw new RuntimeException("Failed to create service " + name
                    + ": service must have a public constructor with a Context argument", ex);
        } catch (InvocationTargetException ex) {
            throw new RuntimeException("Failed to create service " + name
                    + ": service constructor threw an exception", ex);
        }

        startService(service);
        return service;
    } finally {
        Trace.traceEnd(Trace.TRACE_TAG_SYSTEM_SERVER);
    }
}
```

```java
public void startService(@NonNull final SystemService service) {
    // Register it.
    mServices.add(service);
    // Start it.
    long time = SystemClock.elapsedRealtime();
    try {
        service.onStart();
    } catch (RuntimeException ex) {
        throw new RuntimeException("Failed to start service " + service.getClass().getName()
                + ": onStart threw an exception", ex);
    }
    warnIfTooLong(SystemClock.elapsedRealtime() - time, service, "onStart");
}
```

startService方法很简单，是通过传进来的class然后反射创建对应的service服务。所以此处创建的是Lifecycle的实例， 然后通过startService启动了AMS服务

那我们再去看看ActivityManagerService.Lifecycle这个类的构造方法

```java
public static final class Lifecycle extends SystemService {
    private final ActivityManagerService mService;
    private static ActivityTaskManagerService sAtm;

    public Lifecycle(Context context) {
        super(context);
        mService = new ActivityManagerService(context, sAtm);
    }

    public static ActivityManagerService startService(
            SystemServiceManager ssm, ActivityTaskManagerService atm) {
        sAtm = atm;
        return ssm.startService(ActivityManagerService.Lifecycle.class).getService();
    }

    @Override
    public void onStart() {
        mService.start();
    }

    @Override
    public void onBootPhase(int phase) {
        mService.mBootPhase = phase;
        if (phase == PHASE_SYSTEM_SERVICES_READY) {
            mService.mBatteryStatsService.systemServicesReady();
            mService.mServices.systemServicesReady();
        } else if (phase == PHASE_ACTIVITY_MANAGER_READY) {
            mService.startBroadcastObservers();
        } else if (phase == PHASE_THIRD_PARTY_APPS_CAN_START) {
            mService.mPackageWatchdog.onPackagesReady();
        }
    }

    @Override
    public void onUserStopped(@NonNull TargetUser user) {
        mService.mBatteryStatsService.onCleanupUser(user.getUserIdentifier());
    }

    public ActivityManagerService getService() {
        return mService;
    }
}
```

再来看看AMS初始化做了什么

```java

    public ActivityManagerService(Injector injector, ServiceThread handlerThread) {
        final boolean hasHandlerThread = handlerThread != null;
        mInjector = injector;
        mContext = mInjector.getContext();
        mUiContext = null;
        mAppErrors = null;
        mPackageWatchdog = null;
        mAppOpsService = mInjector.getAppOpsService(null /* file */, null /* handler */);
        mBatteryStatsService = null;
        mHandler = hasHandlerThread ? new MainHandler(handlerThread.getLooper()) : null;
        mHandlerThread = handlerThread;//创建Handler线程，用来处理handler消息
        //管理AMS的一些常量，厂商定制系统就可能修改此处
        mConstants = hasHandlerThread
                ? new ActivityManagerConstants(mContext, this, mHandler) : null;
        final ActiveUids activeUids = new ActiveUids(this, false /* postChangesToAtm */);
        mPlatformCompat = null;
        mProcessList = injector.getProcessList(this);
        mProcessList.init(this, activeUids, mPlatformCompat);
        mAppProfiler = new AppProfiler(this, BackgroundThread.getHandler().getLooper(), null);
        mPhantomProcessList = new PhantomProcessList(this);
        mOomAdjuster = hasHandlerThread
                ? new OomAdjuster(this, mProcessList, activeUids, handlerThread) : null;

        mIntentFirewall = hasHandlerThread
                ? new IntentFirewall(new IntentFirewallInterface(), mHandler) : null;
        mProcessStats = null;
        mCpHelper = new ContentProviderHelper(this, false);
        // For the usage of {@link ActiveServices#cleanUpServices} that may be invoked from
        // {@link ActivityTaskSupervisor#cleanUpRemovedTaskLocked}.
        mServices = hasHandlerThread ? new ActiveServices(this) : null;
        mSystemThread = null;
        mUiHandler = injector.getUiHandler(null /* service */);//处理ui相关msg的Handler
        mUidObserverController = new UidObserverController(mUiHandler);
        mUserController = hasHandlerThread ? new UserController(this) : null;
        mPendingIntentController = hasHandlerThread
                ? new PendingIntentController(handlerThread.getLooper(), mUserController,
                        mConstants) : null;
        mProcStartHandlerThread = null;
        mProcStartHandler = null;
        mHiddenApiBlacklist = null;
        mFactoryTest = FACTORY_TEST_OFF;
        mUgmInternal = LocalServices.getService(UriGrantsManagerInternal.class);
        mInternal = new LocalService();
        mPendingStartActivityUids = new PendingStartActivityUids(mContext);
        mUseFifoUiScheduling = false;
        mEnableOffloadQueue = false;
        //初始化管理前台、后台广播的队列， 系统会优先遍历发送前台广播
        mFgBroadcastQueue = mBgBroadcastQueue = mOffloadBroadcastQueue = null;
    }

```

```java
private void start() {
    removeAllProcessGroups();

    mBatteryStatsService.publish();
    mAppOpsService.publish();
    Slog.d("AppOps", "AppOpsService published");
    LocalServices.addService(ActivityManagerInternal.class, mInternal);
    LocalManagerRegistry.addManager(ActivityManagerLocal.class,
            (ActivityManagerLocal) mInternal);
    mActivityTaskManager.onActivityManagerInternalAdded();
    mPendingIntentController.onActivityManagerInternalAdded();
    mAppProfiler.onActivityManagerInternalAdded();
}
```

然后来看看setSystemProcess 干了什么事情

```java
public void setSystemProcess() {
    try {
        ServiceManager.addService(Context.ACTIVITY_SERVICE, this, /* allowIsolated= */ true,
                DUMP_FLAG_PRIORITY_CRITICAL | DUMP_FLAG_PRIORITY_NORMAL | DUMP_FLAG_PROTO);
        ServiceManager.addService(ProcessStats.SERVICE_NAME, mProcessStats);
        ServiceManager.addService("meminfo", new MemBinder(this), /* allowIsolated= */ false,
                DUMP_FLAG_PRIORITY_HIGH);
        ServiceManager.addService("gfxinfo", new GraphicsBinder(this));
        ServiceManager.addService("dbinfo", new DbBinder(this));
        mAppProfiler.setCpuInfoService();
        ServiceManager.addService("permission", new PermissionController(this));
        ServiceManager.addService("processinfo", new ProcessInfoService(this));
        ServiceManager.addService("cacheinfo", new CacheBinder(this));

        ApplicationInfo info = mContext.getPackageManager().getApplicationInfo(
                "android", STOCK_PM_FLAGS | MATCH_SYSTEM_ONLY);
        mSystemThread.installSystemApplicationInfo(info, getClass().getClassLoader());

        synchronized (this) {
            ProcessRecord app = mProcessList.newProcessRecordLocked(info, info.processName,
                    false,
                    0,
                    new HostingRecord("system"));
            app.setPersistent(true);
            app.setPid(MY_PID);
            app.mState.setMaxAdj(ProcessList.SYSTEM_ADJ);
            app.makeActive(mSystemThread.getApplicationThread(), mProcessStats);
            addPidLocked(app);
            updateLruProcessLocked(app, false, null);
            updateOomAdjLocked(OomAdjuster.OOM_ADJ_REASON_NONE);
        }
    } catch (PackageManager.NameNotFoundException e) {
        throw new RuntimeException(
                "Unable to find android system package", e);
    }

    // Start watching app ops after we and the package manager are up and running.
    mAppOpsService.startWatchingMode(AppOpsManager.OP_RUN_IN_BACKGROUND, null,
            new IAppOpsCallback.Stub() {
                @Override public void opChanged(int op, int uid, String packageName) {
                    if (op == AppOpsManager.OP_RUN_IN_BACKGROUND && packageName != null) {
                        if (getAppOpsManager().checkOpNoThrow(op, uid, packageName)
                                != AppOpsManager.MODE_ALLOWED) {
                            runInBackgroundDisabled(uid);
                        }
                    }
                }
            });

    final int[] cameraOp = {AppOpsManager.OP_CAMERA};
    mAppOpsService.startWatchingActive(cameraOp, new IAppOpsActiveCallback.Stub() {
        @Override
        public void opActiveChanged(int op, int uid, String packageName, String attributionTag,
                boolean active, @AttributionFlags int attributionFlags,
                int attributionChainId) {
            cameraActiveChanged(uid, active);
        }
    });
}
```

- 注册服务。首先将ActivityManagerService注册到ServiceManager中，其次将几个与系统性能调试相关的服务注册到ServiceManager。 

- 查询并处理ApplicationInfo。首先调用PackageManagerService的接口，查询包名为android的应用程序的ApplicationInfo信息，对应于framework-res.apk。然后以该信息为参数调用ActivityThread上的installSystemApplicationInfo方法。
- 创建并处理ProcessRecord。调用ActivityManagerService上的newProcessRecordLocked，创建一个ProcessRecord类型的对象，并保存该对象的信息





## 三，与Activity管理有关的数据结构

### ActivityRecord

ActivityRecord，源码中的注释介绍：An entry in the history stack, representing an activity.翻译：历史栈中的一个条目，代表一个activity。 

```java
/**
 * An entry in the history stack, representing an activity. 
 */ 
final class ActivityRecord extends ConfigurationContainer implements AppWindowContainerListener {
    final ActivityManagerService service; // owner 
    final IApplicationToken.Stub appToken; // window manager token 
    AppWindowContainerController mWindowContainerController; 
    final ActivityInfo info; // all about me 
    final ApplicationInfo appInfo; // information about activity's app 
    //省略其他成员变量
    //ActivityRecord所在的TaskRecord
    private TaskRecord task; // the task this is in. 
    //构造方法，需要传递大量信息 
    ActivityRecord(ActivityManagerService _service, ProcessRecord _caller, int _launchedFromPid, int _launchedFromUid, String _launchedFromPackage, Intent _intent, String _resolvedType, ActivityInfo aInfo, Configuration _configuration, com.android.server.am.ActivityRecord _resultTo, String _resultWho, int _reqCode, boolean _componentSpecified, boolean _rootVoiceInteraction, ActivityStackSupervisor supervisor, ActivityOptions options, com.android.server.am.ActivityRecord sourceRecord) {}
}
```

ActivityRecord中存在着大量的成员变量，包含了一个Activity的所有信息。ActivityRecord中的成员变量task表示其所在的TaskRecord，由此可以看出：ActivityRecord与TaskRecord建立了联系

```java
\frameworks\base\services\core\java\com\android\server\am\ActivityStarter.java

private int startActivity(IApplicationThread caller, Intent intent, Intent ephemeralIntent, String resolvedType, ActivityInfo aInfo, ResolveInfo rInfo, IVoiceInteractionSession voiceSession, IVoiceInteractor voiceInteractor, IBinder resultTo, String resultWho, int requestCode, int callingPid, int callingUid, String callingPackage, int realCallingPid, int realCallingUid, int startFlags, SafeActivityOptions options, boolean ignoreTargetSecurity, boolean componentSpecified, ActivityRecord[] outActivity, TaskRecord inTask, boolean allowPendingRemoteAnimationRegistryLookup) {
    ActivityRecord r = new ActivityRecord(mService, callerApp, callingPid, callingUid, callingPackage, intent, resolvedType, aInfo, mService.getGlobalConfiguration(), resultRecord, resultWho, requestCode, componentSpecified, voiceSession != null, mSupervisor, checkedOptions, sourceRecord);
}
```

### TaskRecord

TaskRecord，内部维护一个 ArrayList<ActivityRecord> 用来保存ActivityRecord。

```java
\frameworks\base\services\core\java\com\android\server\am\TaskRecord.java
    
    
class TaskRecord extends ConfigurationContainer implements TaskWindowContainerListener {
    final int taskId; //任务ID
    final ArrayList<ActivityRecord> mActivities; //使用一个ArrayList来保存所有的 ActivityRecord
    private ActivityStack mStack; //TaskRecord所在的ActivityStack */
    TaskRecord(ActivityManagerService service, int _taskId, Intent _intent, Intent _affinityIntent, String _affinity, String _rootAffinity, ComponentName _realActivity, ComponentName _origActivity, boolean _rootWasReset, boolean _autoRemoveRecents, boolean _askedCompatMode, int _userId, int _effectiveUid, String _lastDescription, ArrayList<ActivityRecord> activities, long lastTimeMoved, boolean neverRelinquishIdentity,TaskDescription _lastTaskDescription, int taskAffiliation, int prevTaskId, int nextTaskId, int taskAffiliationColor, int callingUid, String callingPackage, int resizeMode, boolean supportsPictureInPicture, boolean _realActivitySuspended, boolean userSetupComplete, int minWidth, int minHeight) { } 
    //添加Activity到顶部 
    void addActivityToTop(com.android.server.am.ActivityRecord r) { 
        addActivityAtIndex(mActivities.size(), r); 
    }
    //添加Activity到指定的索引位置 
    void addActivityAtIndex(int index, ActivityRecord r) {
        //... 
        r.setTask(this);//为ActivityRecord设置TaskRecord，就是这里建立的联系 
        //... 
        index = Math.min(size, index); 
        mActivities.add(index, r);//添加到mActivities 
        //...
    } 
}
```

可以看到ActivityStack使用了一个ArrayList来保存TaskRecord。另外，ActivityStack中还持有ActivityStackSupervisor对象，这个是用来管理ActivityStacks的。

ActivityStack是由ActivityStackSupervisor来创建的，实际ActivityStackSupervisor就是用来管理ActivityStack的



### ActivityStackSupervisor

ActivityStackSupervisor，顾名思义，就是用来管理ActivityStack的

```java
frameworks/base/services/core/java/com/android/server/am/ActivityStackSupervisor.java


public class ActivityStackSupervisor extends ConfigurationContainer implements DisplayListener { 
    ActivityStack mHomeStack;//管理的是Launcher相关的任务 
    ActivityStack mFocusedStack;//管理非Launcher相关的任务 
    //创建ActivityStack 
    ActivityStack createStack(int stackId, ActivityStackSupervisor.ActivityDisplay display, boolean onTop) {
        switch (stackId) { 
            case PINNED_STACK_ID: //PinnedActivityStack是ActivityStack的子类 
                return new PinnedActivityStack(display, stackId, this, mRecentTasks, onTop); 
            default: 
                //创建一个ActivityStack
                return new ActivityStack(display, stackId, this, mRecentTasks, onTop);
        }
    }
}
```

ActivityStackSupervisor内部有两个不同的ActivityStack对象：mHomeStack、mFocusedStack，用来

管理不同的任务。

ActivityStackSupervisor内部包含了创建ActivityStack对象的方法。

AMS初始化时会创建一个ActivityStackSupervisor对象

![微信图片_20220605203908](https://p3-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/d2cecc9b07214973aec3d5516df7c6f8~tplv-k3u1fbpfcp-zoom-1.image)





## 四，应用启动流程

### 总结



![微信图片_20220605231618](https://p3-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/38cd4827b2a64eef8403a3b4b3bac7dc~tplv-k3u1fbpfcp-zoom-1.image)



![image-20220605204543179](https://p3-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/7ef3f9519fb64d328b5279ae552dd458~tplv-k3u1fbpfcp-zoom-1.image)



1. **Launcher进程请求AMS**

   > 点击图标发生在 Launcher 应用的进程,实际上执行的是 Launcher 的 onClick 方法，在 onClick 里面会执行到Activity 的 startActivity 方法。 startActivity 会调用 mInstrumentation.execStartActivity(); execStartActivity 通过 ActivityManager 的 getService 方法来得到 AMS 的代理对象( Launcher 进程作为客户端与服务端 AMS 不在同一个进程, ActivityManager.getService 返回的是 IActivityManager.Stub 的代理对象,此时如果要实现客户端与服务端进程间的通信， 需要 AMS 继承 IActivityManager.Stub 类并实现相应的方法,这样Launcher进程作为客户端就拥有了服务端AMS的代理对象，然后就可以调用AMS的方法来实现具体功能了)



2. **AMS发送创建应用进程请求，Zygote进程接受请求并fork应用进程**

   > AMS 通过 socket 通信告知 Zygote 进程 fork 子进程。应用进程启动 ActivityThread ,执行 ActivityThread 的 main 方法。main 方法中创建 ApplicationThread ， Looper ， Handler 对象，并开启主线程消息循环 Looper.loop()

3.  **App进程通过Binder向AMS(sytem_server)发起attachApplication请求,AMS绑定ApplicationThread**

   > 在 ActivityThread 的 main 中,通过 ApplicationThread.attach(false, startSeq) ,将 AMS 绑定ApplicationThread 对象,这样 AMS 就可以通过这个代理对象 来控制应用进程。



4. **AMS发送启动Activity的请求**

   > system_server 进程在收到请求后，进行一系列准备工作后，再通过 binder 向App进程发送scheduleLaunchActivity 请求； AMS 将启动 Activity 的请求发送给 ActivityThread 的 Handler 。



5. **ActivityThread的Handler处理启动Activity的请求**

   > App 进程的 binder 线程（ ApplicationThread ）在收到请求后，通过 handler 向主线程发送 LAUNCH_ACTIVITY消息； 主线程在收到 Message 后，通过发射机制创建目标 Activity ，并回调 Activity.onCreate() 等方法。 到此， App 便正式启动，开始进入 Activity 生命周期，执行完 onCreate/onStart/onResume 方法， UI 渲染结束后便可以看到 App 的主界面。



### 源码解析

https://blog.csdn.net/qq_27481249/article/details/116015635

https://zhuanlan.zhihu.com/p/454459946

https://www.its404.com/article/a553181867/89917857

https://www.jianshu.com/p/160a53701ab6



## 五，关于AMS的问题

#### 1. ActivityThread是什么?ApplicationThread是什么?他们的区别

- **ActivityThread**

  > 在Android中它就代表了Android的主线程,它是创建完新进程之后,main函数被加载，然后执行一个loop的循环使当前线程进入消息循环，并且作为主线程。

- **ApplicationThread**

  > ApplicationThread是ActivityThread的内部类， 是一个Binder对象。在此处它是作为IApplicationThread对象的server端等待client端的请求然后进行处理，最大的client就是AMS。



#### 2. Instrumentation是什么？和ActivityThread是什么关系？

- AMS与ActivityThread之间诸如Activity的创建、暂停等的交互工作实际上是由Instrumentation具体操作的。每个Activity都持有一个Instrumentation对象的一个引用， 整个进程中是只有一个Instrumentation。
- mInstrumentation的初始化在ActivityThread::handleBindApplication函数。
- 可以用来独立地控制某个组件的生命周期。
- Activity`的`startActivity方法。startActivity会调用mInstrumentation.execStartActivity(); 
- mInstrumentation 调用用 AMS , AMS 通过 socket 通信告知 Zygote 进程 fork 子进程。





#### 3. ActivityManagerService和zygote进程通信是如何实现的

应用启动时，Launcher进程请求AMS，AMS发送创建应用进程请求，Zygote进程接受请求并fork应用进程。而AMS发送创建应用进程请求调用的是 ZygoteState.connect() 方法，ZygoteState 是 ZygoteProcess 的内部类。

```
public static ZygoteState connect(LocalSocketAddress address) throws IOException {
          DataInputStream zygoteInputStream = null;
          BufferedWriter zygoteWriter = null;
          final LocalSocket zygoteSocket = new LocalSocket();
           try {
              zygoteSocket.connect(address);
               zygoteInputStream = new DataInputStream(zygoteSocket.getInputStream());
               zygoteWriter = new BufferedWriter(new OutputStreamWriter(
                      zygoteSocket.getOutputStream()), 256);
          } catch (IOException ex) {
              try {
                  zygoteSocket.close();
              } catch (IOException ignore) {
              }
               throw ex;
          }
           return new ZygoteState(zygoteSocket, zygoteInputStream, zygoteWriter,
                  Arrays.asList(abiListString.split(",")));
      }
复制代码
```

Zygote 处理客户端请求：Zygote 服务端接收到参数之后调用 ZygoteConnection.processOneCommand() 处理参数，并 fork 进程。

最后通过 findStaticMain() 找到 ActivityThread 类的 main() 方法并执行，子进程就这样启动了。



#### 4. Activity的启动的整体流程：

> **1. Launcher进程请求AMS**
>
> **2. AMS发送创建应用进程请求**
>
> **3. Zygote进程接受请求并孵化应用进程**
>
> **4. 应用进程启动ActivityThread**
>
> **5. 应用进程绑定到AMS**
>
> **6. AMS发送启动Activity的请求**
>
> **7. ActivityThread的Handler处理启动Activity的请求**



#### 5.
