---
title: 性能优化-App启动优化
date: 2022-06-28 01:14:29
tags:
  - Android
  - FrameWork
  - 性能优化
---

# 性能优化-App启动优化

## 启动状态

应用有三种启动状态，每种状态都会影响应用向用户显示所需的时间：冷启动、温启动与热启动。在冷启动中，应用从头开始启动。在另外两种状态中，系统需要将后台运行的应用带入前台。建议始终在假定冷启动的基础上进行优化。这样做也可以提升温启动和热启动的性能。



> - 冷启动
>   - 冷启动是指应用从头开始启动：系统进程在冷启动后才创建应用进程。发生冷启动的情况包括应用自设备启动后或系统终止应用后首次启动。
>
> - 热启动：
>   - 在热启动中，系统的所有工作就是将 Activity 带到前台。只要应用的所有 Activity 仍驻留在内存中，应用就不必重复执行对象初始化、布局加载和绘制。
>
> - 温启动
>   - 温启动包含了在冷启动期间发生的部分操作；同时，它的开销要比热启动高。有许多潜在状态可视为温启动。例如：
>     - 用户在退出应用后又重新启动应用。进程可能未被销毁，继续运行，但应用需要执行onCreate() 从头开始重新创建 Activity。
>     - 系统将应用从内存中释放，然后用户又重新启动它。进程和 Activity 需要重启，但传递到onCreate() 的已保存的实例 state bundle 对于完成此任务有一定助益。


<!--more-->



## 冷启动耗时统计



### 系统日志统计

在 Android 4.4（API 级别 19）及更高版本中，logcat 包含一个输出行，其中包含名为 Displayed 的值。此值代表从启动进程到在屏幕上完成对应 Activity 的绘制所用的时间。

```
ActivityManager: Displayed com.android.myexample/.StartupTiming: +3s534ms
```

如果我们使用异步懒加载的方式来提升程序画面的显示速度，这通常会导致的一个问题是，程序画面已经显示，同时 Displayed 日志已经打印，可是内容却还在加载中。为了衡量这些异步加载资源所耗费的时间，我们可以在异步加载完毕之后调用 activity.reportFullyDrawn() 方法来让系统打印到调用此方法为止的启动耗时。



### **adb** 命令统计

查看启动时间的另一种方式是使用命令：

```
adb [-d|-e|-s <serialNumber>] shell am start -S -W com.example.app/.MainActivity -c android.intent.category.LAUNCHER -a android.intent.action.MAIN
```

启动完成后，将输出：

```java
ThisTime: 415
TotalTime: 415
WaitTime: 437
```

- WaitTime:总的耗时，包括前一个应用Activity pause的时间和新应用启动的时间；
- ThisTime表示一连串启动Activity的最后一个Activity的启动耗时；
- TotalTime表示新应用启动的耗时，包括新进程的启动和Activity的启动，但不包括前一个应用Activity pause的耗时。

开发者一般只要关心**TotalTime**即可，这个时间才是自己应用真正启动的耗时。



## CPU Profifile

要在应用启动过程中自动开始记录 CPU 活动，请执行以下操作：

1. 依次选择 **Run > Edit Confifigurations**。 

   ![微信图片_20220609232523](https://s2.loli.net/2022/06/09/g9ET4afuBpOwNXj.png)

2.  在 **Profifiling** 标签中，勾选 **Start recording CPU activity on startup** 旁边的复选框。

   ![微信图片_20220609232604](https://s2.loli.net/2022/06/09/l4UT7hoMuGNCm3J.png)

3. 从菜单中选择 CPU 记录配置。

   - **Sample Java Methods**

     > 对 Java 方法采样：在应用的 Java 代码执行期间，频繁捕获应用的调用堆栈。分析器会比较捕获的数据集，
     >
     > 以推导与应用的 Java 代码执行有关的时间和资源使用信息。如果应用在捕获调用堆栈后进入一个方法并在下
     >
     > 次捕获前退出该方法，分析器将不会记录该方法调用。如果您想要跟踪生命周期如此短的方法，应使用检测
     >
     > 跟踪。

   - **Trace Java Methods**

     > 跟踪 Java 方法：在运行时检测应用，以在每个方法调用开始和结束时记录一个时间戳。系统会收集并比较这
     >
     > 些时间戳，以生成方法跟踪数据，包括时间信息和 CPU 使用率。

   - **Sample C/C++ Functions**

     > 对 C/C++ 函数采样：捕获应用的原生线程的采样跟踪数据。要使用此配置，您必须将应用部署到搭载
     >
     > Android 8.0（API 级别 26）或更高版本的设备上。

   - **Trace System Calls**

     > 跟踪系统调用：捕获非常翔实的细节，以便您检查应用与系统资源的交互情况。您可以检查线程状态的确切
     >
     > 时间和持续时间、直观地查看所有内核的 CPU 瓶颈在何处，并添加要分析的自定义跟踪事件。要使用此配
     >
     > 置，您必须将应用部署到搭载 Android 7.0（API 级别 24）或更高版本的设备上。
     >
     > 
     >
     > 此跟踪配置在 systrace 的基础上构建而成。您可以使用 systrace 命令行实用程序指定除 CPU Profifiler 提供的
     >
     > 选项之外的其他选项。systrace 提供的其他系统级数据可帮助您检查原生系统进程并排查丢帧或帧延迟问
     >
     > 题。

   4. 点击 **Apply**。 

   5. 依次选择 **Run > Profifile**，将您的应用部署到搭载 Android 8.0（API 级别 26）或更高版本的设备上。

      ![微信图片_20220609232857](https://s2.loli.net/2022/06/09/YvmVOj7yZBUlFHX.png)

   点击Stop，结束跟踪后显示：

   ![微信图片_20220609232942](https://s2.loli.net/2022/06/09/uBP6WOzUalGJZDd.png)



### **Call Chart**

以图形来呈现方法跟踪数据或函数跟踪数据，其中调用的时间段和时间在横轴上表示，而其被调用方则在纵轴上显示。对系统 API 的调用显示为橙色，对应用自有方法的调用显示为绿色，对第三方 API（包括 Java 语言 API）的调用显示为蓝色。 **（实际颜色显示有Bug）**

![微信图片_20220609233124](C:%5CUsers%5Claibinzhi%5CDesktop%5C%E5%BE%AE%E4%BF%A1%E5%9B%BE%E7%89%87_20220609233124.png)

Call Chart 已经比原数据可读性高很多，但它仍然不方便发现那些运行时间很长的代码，这时我们便需要使用Flame Chart。



### **Flame Chart**

提供一个倒置的调用图表，用来汇总完全相同的调用堆栈。也就是说，将具有相同调用方顺序的完全相同的方法或函数收集起来，并在火焰图中将它们表示为一个较长的横条 。

横轴显示的是百分比数值。由于忽略了时间线信息，Flame Chart 可以展示每次调用消耗时间占用整个记录时长的百分比。 同时纵轴也被对调了，在顶部展示的是被调用者，底部展示的是调用者。此时的图表看起来越往上越窄，就好像火焰一样，因此得名: **火焰图。**

> 说白了就是将Call Chart上下调用栈倒过来。

![image-20220609233232739](https://s2.loli.net/2022/06/09/B79i4kSMoDz6FCd.png)

### **Top Down Tree**

如果我们需要更精确的时间信息，就需要使用 Top Down Tree。 Top Down Tree显示一个调用列表，在该列表中展开方法或函数节点会显示它调用了的方法节点。

对于每个节点，三个时间信息:

- Self Time —— 运行自己的代码所消耗的时间；
- Children Time —— 调用其他方法的时间；
- Total Time —— 前面两者时间之和。

**此视图能够非常方便看到耗时最长的方法调用栈。**



### **Bottom Up Tree**

方便地找到某个方法的调用栈。在该列表中展开方法或函数节点会显示哪个方法调用了自己。



### **Debug API**

除了直接使用 **Profifile** 启动之外，我们还可以借助Debug API生成trace文件。

```java
public class MyApplication extends Application { 
    public MyApplication() { 
        Debug.startMethodTracing("test");
    }
    //
    ..... 
}
public class MainActivity extends AppCompatActivity { 
    @Override public void onWindowFocusChanged(boolean hasFocus) { 
        super.onWindowFocusChanged(hasFocus); 
        Debug.stopMethodTracing();
    }
    //
    .......
}
```

运行App，则会在sdcard中生成一个enjoy.trace文件（需要sdcard读写权限）。将手机中的trace文件保存至电脑，随后拖入Android Studio即可。



### 总结

通过工具可以定位到耗时代码，然后查看是否可以进行优化。对于APP启动来说，启动耗时包括Android系统启动APP进程加上APP启动界面的耗时时长，我们可做的优化是APP启动界面的耗时，也就是说从Application的构建到主界面的 onWindowFocusChanged 的这一段时间。



## StrictMode严苛模式

StrictMode是一个开发人员工具，它可以检测出我们可能无意中做的事情，并将它们提请我们注意，以便我们能够

修复它们。

StrictMode最常用于捕获应用程序主线程上的意外磁盘或网络访问。帮助我们让磁盘和网络操作远离主线程，可以

使应用程序更加平滑、响应更快。



```java
public class MyApplication extends Application {
    @Override
    public void onCreate() {
        if (BuildConfig.DEBUG) {
            //线程检测策略
            StrictMode.setThreadPolicy(new StrictMode.ThreadPolicy.Builder()
                    .detectDiskReads() //读、写操作
                    .detectDiskWrites()
                    .detectNetwork() // or .detectAll() for all detectable problems
                    .penaltyLog().build());
            StrictMode.setVmPolicy(new StrictMode.VmPolicy.Builder()
                    .detectLeakedSqlLiteObjects() //Sqlite对象泄露
                    .detectLeakedClosableObjects() //未关闭的Closable对象泄露
                    .penaltyLog() //违规打印日志
                    .penaltyDeath() //违规崩溃 
                    .build());
        }
    }
}
```





## **启动黑白屏**

当系统加载并启动 App 时，需要耗费相应的时间，这样会造成用户会感觉到当点击 App 图标时会有 “延迟” 现象，为了解决这一问题，Google 的做法是在 App 创建的过程中，先展示一个空白页面，让用户体会到点击图标之后立马就有响应。

如果你的application或activity启动的过程太慢，导致系统的BackgroundWindow没有及时被替换，就会出现启动时白屏或黑屏的情况（取决于Theme主题是Dark还是Light）。消除启动时的黑/白屏问题，大部分App都采用自己在Theme中设置背景图的方式来解决。

```xml
<style name="AppTheme.Launcher">
    <item name="android:windowBackground">@drawable/bg</item> 
</style> 
<activity 
          android:name=".activity.SplashActivity"
          android:screenOrientation="portrait" 
          android:theme="@style/AppTheme.Launcher"> 
    <intent-filter> 
        <action android:name="android.intent.action.MAIN" /> 
        <category android:name="android.intent.category.LAUNCHER" />
    </intent-filter> 
</activity>
```

然后在Activity的onCreate方法，把Activity设置回原来的主题。

```java
@Override protected void onCreate(Bundle savedInstanceState) { 
    //替换为原来的主题在onCreate之前调用
    setTheme(R.style.AppTheme); 
    super.onCreate(savedInstanceState); 
}
```

这么做，只是提高启动的用户体验。并不能做到真正的加快启动速度



## 总结



### 总体

1. 合理的使用异步初始化、延迟初始化、懒加载机制。
2. 启动过程避免耗时操作，如数据库 I/O操作不要放在主线程执行。
3. 类加载优化：提前异步执行类加载。
4. 合理使用IdleHandler进行延迟初始化。
5. 简化布局





### 启动流程

1. 点击桌面App图标，Launcher进程采用Binder IPC向system_server进程发起startActivity请求；
2. system_server进程接收到请求后，向zygote进程发送创建进程的请求；
3. Zygote进程fork出新的子进程，即App进程；
4. App进程，通过Binder IPC向sytem_server进程发起attachApplication请求；
5. system_server进程在收到请求后，进行一系列准备工作后，再通过binder IPC向App进程发送scheduleLaunchActivity请求；
6. App进程的binder线程（ApplicationThread）在收到请求后，通过handler向主线程发送LAUNCH_ACTIVITY消息；
7. 主线程在收到Message后，通过反射机制创建目标Activity，并回调Activity.onCreate()等方法。
8. 到此，App便正式启动，开始进入Activity生命周期，执行完onCreate/onStart/onResume方法，UI渲染结束后便可以看到App的主界面。
9. Application的构建到主界面的 onWindowFocusChanged 的这一段时间可以去优化

![image-20220610000026013](https://s2.loli.net/2022/06/10/U1oYNrZODnxWzBv.png)





### 启动加载常见优化策略

一个应用越大，涉及模块越多，包含的服务甚至进程就会越多，如网络模块的初始化，底层数据初始化等，这些加载都需要提前准备好，有些不必要的就不要放到应用中。通常可以从以下四个维度整理启动的各个点：

1、必要且耗时：启动初始化，考虑用线程来初始化

2、必要不耗时：不用处理

3、非必要耗时，数据上报、插件初始化，按需处理

4、非必要不耗时：直接去掉，有需要的时候再加载

将应用启动时要执行的内容按上述分类，按需实现加载逻辑。那么常见的优化加载策略有哪些呢？

**异步加载**：耗时多的加载放到子线程中异步执行

**延迟加载**: 非必须的数据延迟加载

**提前加载**：利用ContentProvider提前进行初始化



### 异步加载

异步加载，简单来说，就是使用子线程异步加载。在实际场景中，启动时常常需要对各种第三方库做初始化操作。通过将初始化放到子线程中进行，可以大大加快启动。但是通常，有些业务逻辑是要再第三方库的初始化后才能正常运行的，这时候如果只是简单的放到子线程中跑，不做限制就很可能出现在没初始化完成就跑业务逻辑，导致异常。这种较为复杂的情况下，可以采用CountDownLatch处理，或者是使用启动器的思想处理。



CountDownLatch使用

```java
class MyApplication extends Application {

    // 线程等待锁
    private CountDownLatch mCountDownLatch = new CountDownLatch(1);

    // CPU核数
    private static final int CPU_COUNT = Runtime.getRuntime().availableProcessors();
    // 核心线程数
    private static final int CORE_POOL_SIZE = Math.max(2, Math.min(CPU_COUNT - 1, 4));

    void onCreate() {
        ExecutorService service = Executors.newFixedThreadPool(CORE_POOL_SIZE);
        service.submit(new Runnable() {
            @Override public void run() {
                //初始化weex，因为Activity加载布局要用到需要提前初始化完成
                initWeex();
                mCountDownLatch.countDown();
            }
        });

        service.submit(new Runnable() {
            @Override public void run() {
                //初始化Bugly,无需关心是否在界面绘制前初始化完
                initBugly();
            }
        });

        //提交其他库初始化，此处省略。。。

        try {
            //等待weex初始化完才走完onCreate
            mCountDownLatch.await();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}

```



使用CountDownLatch在初始化的逻辑不复杂的情况下推荐使用。但如果初始化的几个库之间又有相互依赖，逻辑复杂的情况下，则推荐使用加载器的方式。

启动器的核心如下：

- 充分利用CPU多核能力，自动梳理并顺序执行任务；
- 代码Task化，将启动任务抽象成各个task；
- 根据所有任务依赖关系排序生成一个有向无环图；
- 多线程按照线程优先级顺序执行

具体实现可参考：[github.com/NoEndToLF/A…](https://links.jianshu.com/go?to=https%3A%2F%2Fgithub.com%2FNoEndToLF%2FAppStartFaster)





### 延迟加载

有些第三方库的初始化其实优先级并不高，可以按需加载。或者是利用IdleHandler在主线程空闲的时候进行分批初始化。按需加载可根据具体情况实现，这里不做赘述。这里介绍下使用IdleHandler的使用

```java
 private MessageQueue.IdleHandler mIdleHandler = new MessageQueue.IdleHandler() {
        @Override
        public boolean queueIdle() {
            //当return true时，会移除掉该IdleHandler，不再回调，当为false，则下次主线程空闲时会再次回调
            return false;
        }
    };

```

使用IdleHandler做分批初始化，为什么要分批？当主线程空闲时，执行IdleHandler，但如果IdleHandler内容太多，则还是会导致卡顿。因此最好是将初始化操作分批在主线程空闲时进行

```java
public class DelayInitDispatcher {

    private Queue<Task> mDelayTasks = new LinkedList<>();

    private MessageQueue.IdleHandler mIdleHandler = new MessageQueue.IdleHandler() {
        @Override
        public boolean queueIdle() {
            //每次执行一个Task，实现分批进行
            if(mDelayTasks.size()>0){
                Task task = mDelayTasks.poll();
                new DispatchRunnable(task).run();
            }
            //当为空时，返回false，移除IdleHandler
            return !mDelayTasks.isEmpty();
        }
    };

    //添加初始化任务
    public DelayInitDispatcher addTask(Task task){
        mDelayTasks.add(task);
        return this;
    }

    //给主线程添加IdleHandler
    public void start(){
        Looper.myQueue().addIdleHandler(mIdleHandler);
    }

}
```



### 提前加载

上述方案中初始化最快的时机都是在Application的onCreate中进行，但还有更早的方式。ContentProvider的onCreate是在Application的attachBaseContext和onCreate方法中间进行的。也就是说它比Application的onCreate方法更早执行。所以可以利用这点来对第三方库的初始化进行提前加载。

androidx-startup使用

```java
如何使用：
第一步，写一个类实现Initializer,泛型为返回的实例，如果不需要的话，就写Unit
class TimberInitializer : Initializer<Unit> {

    //这里写初始化执行的内容，并返回初始化实例
    override fun create(context: Context) {
        if (BuildConfig.DEBUG) {
            Timber.plant(Timber.DebugTree())
            Timber.d("TimberInitializer is initialized.")
        }
    }

    //这里写初始化的东西依赖的另外的初始化器，没有的时候返回空List
    override fun dependencies(): List<Class<out Initializer<*>>> {
        return emptyList()
    }

}

第二步，在AndroidManifest中声明provider，并配置meta-data写初始化的类
<provider
    android:name="androidx.startup.InitializationProvider"
    android:authorities="com.test.pokedex.androidx-startup"
    android:exported=“false"
    //这里写merge是因为其他模块可能也有同样的provider声明，做合并操作
    tools:node="merge">
    //当有相互依赖的情况下，写顶层的初始化器就可以，其依赖的会自动搜索到
    <meta-data
        android:name="com.test.pokedex.initializer.TimberInitializer"
        android:value="androidx.startup" />
</provider>

```



### **MutilDex 优化**



问题：dex 的指令格式设计并不完善，单个 dex 文件中引用的 Java 方法总数不能超过 65536 个，在方法数超过 65536 的情况下，将拆分成多个 dex。一般情况下 Dalvik 虚拟机只能执行**经过优化后的 odex 文件**，在 4.x 设备上为了提升应用安装速度，其在安装阶段**仅会对应用的首个 dex 进行优化**。对于非首个 dex 其会在首次运行调用**MultiDex.install 时进行优化**，而这个优化是非常耗时的，这就造成了 4.x 设备上首次启动慢的问题。



解决办法：

破坏“Dalvik 虚拟机需要加载 odex”这一限制，即绕过 Dalvik 的限制直接加载未经优化的 dex。这个方案的核心在 Dalvik_dalvik_system_DexFile_openDexFile_bytearray 这个 native 函数，它支持加载未经优化后的 dex 文件。具体的优化方案如下：

> 1. 首先从 APK 中解压获取原始的非首个 dex 文件的字节码；
> 2. 调用 Dalvik_dalvik_system_DexFile_openDexFile_bytearray，逐个传入之前从 APK 获取的 DEX 字节码，完成 DEX 加载，得到合法的 DexFile 对象；
> 3. 将 DexFile 都添加到 APP 的 PathClassLoader 的 DexPathList 里；
> 4. 延后异步对非首个 dex 进行 odex 优化。



引入库[BoostMultiDex](https://github.com/bytedance/BoostMultiDex)

