---
title: Android Framework之WMS
date: 2022-06-28 00:59:29
tags:
  - Android
  - FrameWork
  - 源码
---




# Android Framework之WMS

## 序言

- [Android-UI绘制流程及原理1](https://juejin.cn/post/7101608284439707662)
- [Android-UI绘制流程及原理2](https://juejin.cn/post/7101608589353025544)


<!--more-->




## 一，WMS基础知识

### 1. WindowManagerService

#### 1.1 定义

Framework层的窗口管理服务，职责是管理Android系统中的所有的Window。窗口管理服务，继承IWindowManager.Stub，Binder服务端，因此WM与WMS的交互也是一个IPC的过程

##### 1.1.1 Z-ordered的维护函数

##### 1.1.2 输入法管理

##### 1.1.3 AddWindow/RemoveWindow

##### 1.1.4 Layerout

##### 1.1.5 Token管理，AppToken

##### 1.1.6 活动窗口管理（FocusWindow）

##### 1.1.7 活动应用管理（FocusAPP）

##### 1.1.8 转场动画

##### 1.1.9 系统消息收集线程

##### 1.1.10 系统消息分发线程



#### 1.2 Window

手机上一块显示区域，添加一个Window的过程，也就是申请分配一块Surface的过程



#### 1.3 Surface

每个显示界面的窗口都是一个Surface



#### 1.4 WindowManager（WM）

应用与窗口管理服务WindowManagerService交互的接口



#### 1.5 PhoneWindowManager

实现了窗口的各种策略，定义了窗口相关策略，比如：告诉WMS某一个类型Window的Z-Order的值是多少，帮助WMS矫正不合理的窗口属性，为WMS监听屏幕旋转的状态，预处理一些系统按键事件（例如HOME、BACK键等的默认行为就是在这里实现的）等



#### 1.6 Choreographer

用于控制窗口动画、屏幕旋转等操作,它拥有从显示子系统获取VSYNC同步事件的能力，从而可以在合适的时机通知渲染动作，避免在渲染的过程中因为发生屏幕重绘而导致的画面撕裂。WMS使用Choreographer负责驱动所有的窗口动画、屏幕旋转动画、墙纸动画的渲染



#### 1.7 DisplayContent

- 用于描述多屏输出相关信息。
- 根据窗口的显示位置将其分组。隶属于同一个DisplayContent的窗口将会被显示在同一个屏幕中。每一个DisplayContent都对应这唯一ID，在添加窗口时可以通过指定这个ID决定其将被显示在那个屏幕中。
- DisplayContent是一个非常具有隔离性的一个概念。处于不同DisplayContent的两个窗口在布局、显示顺序以及动画处理上不会产生任何耦合



#### 1.8 WindowState

描述窗口的状态信息以及和WindowManagerService进行通信，一般一个窗口对应一个WindowState。它用来表示一个窗口的所有属性



#### 1.9 WindowToken

**窗口Token，用来做Binder通信；同时也是一种标识**

1. 在进行窗口Zorder排序时，属于同一个WindowToken的窗口会被安排在一起，而且在其中定义的一些属性将会影响所有属于此WindowToken的窗口，这些都表明了属于同一个WindowToken的窗口之间的紧密联系
1. 应用组件在需要新的窗口时，必须提供WindowToken以表明自己的身份，并且窗口的类型必须与所持有的WindowToken的类型一致
1. 在创建系统类型的窗口时不需要提供一个有效的Token，WMS会隐式地为其声明一个WindowToken，看起来谁都可以添加个系统级的窗口。难道Android为了内部使用方便而置安全于不顾吗？非也，addWindow()函数一开始的mPolicy.checkAddPermission()的目的就是如此。它要求客户端必须拥有SYSTEM_ALERT_WINDOW或INTERNAL_SYSTEM_WINDOW权限才能创建系统类型的窗口



#### 1.10 Session

App进程通过建立Session代理对象和Session对象通信，进而和WMS建立连接



#### 1.11 SurfaceFlinger

SurfaceFlinger负责管理Android系统的帧缓冲区（Frame Buffer)，Android设备的显示屏被抽象为一个帧缓冲区，而Android系统中的SurfaceFlinger服务就是通过向这个帧缓冲区写入内容来绘制应用程序的用户界面的



#### 1.12 InputManager

IMS实例。管理每个窗口的输入事件通道（InputChannel）以及向通道上派发事件



#### 1.13 Animator

所有窗口动画的总管（WindowStateAnimator对象）。在Choreographer的驱动下，逐个渲染所有的动画



### 2. Activity相关变量

#### 2.1 mWindow

PhoneWindow对象，继承于Window，是窗口对象

#### 2.2 mWindowManager

WindowManagerImpl对象，实现WindowManager接口

#### 2.3 mMainThread

Activity对象，并非真正的线程，是运行在主线程里的对象

#### 2.4 mUIThread

Thread对象，主线程

#### 2.5 mHandler

Handler对象，主线程Handler

#### 2.6 mDecor

View对象，用来显示Activity里的视图



### 3. WMS启动流程分析



#### 3.1 SystemServer.startOtherServices

##### 3.1.1 WindowManagerService.main

> 1. WindowManagerService.main
>
> 2. DisplayThread.getHandler().runWithScissors 同步等待WMS初始化成功 
>
> 3. new WindowManagerService

##### 3.1.2 mActivityManagerService.setWindowManager(wm)

##### 3.1.3 wm.onInitReady() -> initPolicy->runWithScissors

##### 3.1.4 wm.displayReady()  初始化显示尺寸信息，结束后WMS会根据AMS进行一次configure

##### 3.1.5 wm.systemReady()  直接调用mPolicy的systemready方法



#### 3.2 WMS重要成员变量

##### 3.2.1 mTokenMap

**保存所有显示令牌（类型为WindowToken），一个窗口必须隶属于某一个显示令牌。衍生变量还有：**

> 1. mAppTokens，保存了所有属于Activity的显示令牌（WindowToken的子类AppWindowToken），mAppTokens列表是有序的，它与AMS中的mHistory列表的顺序保持一致，反映了系统中Activity的顺序。
> 2. mExitingTokens，保存了正在退出过程中的显示令牌等

##### 3.2.2 mWindowMap

**保存所有窗口的状态信息（类型为WindowState），衍生变量还有**

> 1. mPendingRemove，保存了那些退出动画播放完成并即将被移除的窗口
> 2. mLosingFocus，保存了那些失去了输入焦点的窗口
> 3. 在DisplayContent中，也有一个windows列表，这个列表存储了显示在此DisplayContent中的窗口，并且它是有序的。窗口在这个列表中的位置决定了其最终显示时的Z序

##### 3.2.3 mSessions

**保存了当前所有想向WMS寻求窗口管理服务的客户端。注意Session是具有进程唯一性**

#### 3.3 总结

> 1. WMS的启动主要涉及3个线程：system_server、android.display、android.ui；其中WMS.H.handleMessage 运行在android.display线程中
> 2. WMS中3个关键步骤：创建WMS对象，初始化显示信息，处理systemready通知



### 4. 窗口类型

#### 1. 应用窗口 (Application Window)

包括所有应用程序自己创建的窗口，以及在应用起来之前系统负责显示的窗口，层级范围是1~99

```java
//第一个应用窗口 
public static final int FIRST_APPLICATION_WINDOW = 1; 
//所有程序窗口的base窗口，其他应用程序窗口都显示在它上面 
public static final int TYPE_BASE_APPLICATION = 1;
//所有Activity的窗口，只能配合Activity在当前APP使用 
public static final int TYPE_APPLICATION = 2; 
//目标应用窗口未启动之前的那个窗口 
public static final int TYPE_APPLICATION_STARTING = 3; 
//最后一个应用窗口 
public static final int LAST_APPLICATION_WINDOW = 99;
```



#### 2. 子窗口(Sub Window)

应用自定义的对话框，或者输入法窗口，子窗口必须依附于某个应用窗口（设置相同的token)，层级范围是1000~1999

```java
//第一个子窗口
public static final int FIRST_SUB_WINDOW = 1000;
// 面板窗口，显示于宿主窗口的上层,只能配合Activity在当前APP使用
public static final int TYPE_APPLICATION_PANEL = FIRST_SUB_WINDOW; 
// 媒体窗口（例如视频），显示于宿主窗口下层 
public static final int TYPE_APPLICATION_MEDIA = FIRST_SUB_WINDOW+1; 
// 应用程序窗口的子面板，只能配合Activity在当前APP使用 (PopupWindow默认就是这个Type) 
public static final int TYPE_APPLICATION_SUB_PANEL = FIRST_SUB_WINDOW+2; 
//对话框窗口,只能配合Activity在当前APP使用 
public static final int TYPE_APPLICATION_ATTACHED_DIALOG = FIRST_SUB_WINDOW+3; //
public static final int TYPE_APPLICATION_MEDIA_OVERLAY = FIRST_SUB_WINDOW+4; 
//最后一个子窗口 
public static final int LAST_SUB_WINDOW = 1999;
```



#### 3. 子窗口(Sub Window)

系统设计，不依附于任何应用窗口，比如：状态栏(Status Bar)、导航栏(Navigation Bar)、壁纸(Wallpaper)、来电显示窗口(Phone)、锁屏窗口(KeyGuard)、信息提示窗口(Toast)、音量调整窗口、鼠标光标等等，层级范围是2000~2999



```java
//系统窗口，非应用程序创建
public static final int FIRST_SYSTEM_WINDOW = 2000;

//状态栏，只能有一个状态栏，位于屏幕顶端，其他窗口都位于它下方 
public static final int TYPE_STATUS_BAR = FIRST_SYSTEM_WINDOW; 
//搜索栏，只能有一个搜索栏，位于屏幕上方 
public static final int TYPE_SEARCH_BAR = FIRST_SYSTEM_WINDOW+1; 
//电话窗口，它用于电话交互（特别是呼入），置于所有应用程序之上，状态栏之下,属于悬浮窗(并且给一个Activity的话按下HOME键会出现看 不到桌面上的图标异常情况)
public static final int TYPE_PHONE = FIRST_SYSTEM_WINDOW+2; 
//系统警告提示窗口，出现在应用程序窗口之上,属于悬浮窗, 但是会被禁止 
public static final int TYPE_SYSTEM_ALERT = FIRST_SYSTEM_WINDOW+3; 
//信息窗口，用于显示Toast, 不属于悬浮窗, 但有悬浮窗的功能, 缺点是在Android2.3上无法接收点击事件 
public static final int TYPE_TOAST = FIRST_SYSTEM_WINDOW+5; 
public static final int TYPE_KEYGUARD = FIRST_SYSTEM_WINDOW+4; 
//锁屏窗口
public static final int TYPE_KEYGUARD = FIRST_SYSTEM_WINDOW+4; 
//系统顶层窗口，显示在其他一切内容之上，此窗口不能获得输入焦点，否则影响锁屏
public static final int TYPE_SYSTEM_OVERLAY = FIRST_SYSTEM_WINDOW+6;
//电话优先，当锁屏时显示，此窗口不能获得输入焦点，否则影响锁屏
public static final int TYPE_PRIORITY_PHONE = FIRST_SYSTEM_WINDOW+7;
//系统对话框窗口
public static final int TYPE_SYSTEM_DIALOG = FIRST_SYSTEM_WINDOW+8; 
//锁屏时显示的对话框 
public static final int TYPE_KEYGUARD_DIALOG = FIRST_SYSTEM_WINDOW+9; 
//系统内部错误提示，显示在任何窗口之上 
public static final int TYPE_SYSTEM_ERROR = FIRST_SYSTEM_WINDOW+10; 
//内部输入法窗口，显示于普通UI之上，应用程序可重新布局以免 被此窗口覆盖
public static final int TYPE_INPUT_METHOD = FIRST_SYSTEM_WINDOW+11;
//内部输入法对话框，显示于当前输入法窗口之上 
public static final int TYPE_INPUT_METHOD_DIALOG= FIRST_SYSTEM_WINDOW+12;
//墙纸窗口
public static final int TYPE_WALLPAPER = FIRST_SYSTEM_WINDOW+13;
//状态栏的滑动面板 
public static final int TYPE_STATUS_BAR_PANEL = FIRST_SYSTEM_WINDOW+14;
//安全系统覆盖窗口，这些窗户必须不带输入焦点，否则会干扰键盘 
public static final int TYPE_SECURE_SYSTEM_OVERLAY = FIRST_SYSTEM_WINDOW+15; 
//最后一个系统窗口 
public static final int LAST_SYSTEM_WINDOW = 2999;
```





## 二，从Activity启动角度看WMS

### 1. Activity.attach

**从handleLaunchActivity->...->performLaunchActivity->...->activity.attach**

#### 1.1 mWindow = new PhoneWindow  创建Window对象

#### 1.2 mWindow.setWindowManager 创建WindowManager对象

- Window.setWindowManager 

-  WindowManagerImpl.createLocalWindowManager 

- new WindowManagerImpl

  > WindowManagerGlobal mGlobal = WindowManagerGlobal.getInstance
  >
  > 实际上WindowManagerImpl类中的各种方法最后都是转调WindowManagerGlobal来实现，由此可见，一个应用中所有的Activity都是通过这个进程内唯一的WindowManagerGlobal对象和WMS之间进行通信， WindowManagerGlobal中有3个重要的成员变量
  >
  > *//保存所有顶层View的对象(DecorView)*
  >
  >  private final ArrayList<View> mViews = new ArrayList<View>();
  >
  > *//保存和顶层View相关联的ViewRootImpl对象*
  >
  > private final ArrayList<ViewRootImpl> mRoots = new ArrayList<ViewRootImpl>();
  >
  > *//保存创建顶层View的layout参数*
  >
  > private final ArrayList<WindowManager.LayoutParams> mParams =    
  >
  >  new ArrayList<WindowManager.LayoutParams>()

#### 1.3 mWindowManager = mWindow.getWindowManager

*将之前创建的WindowManager对象保存在mWindowManager对象中*



### 2. ActivityThread.handleResumeActivity

#### 2.1 activity.makeVisible

##### 2.1.1 WindowManagerImpl.addView

##### 2.1.2 WindowManagerGlobal.addView

###### 2.1.2.1 root = new ViewRootImpl

###### 2.1.2.2 mViews.add(view)

###### 2.1.2.3 mRoots.add(root)

###### 2.1.2.4 mParams.add(wparams)

###### 2.1.2.5 root.setView

1. mWindowSession.addToDisplay Session在app的代理，实际上调用了Session的addToDisplay
2. addToDisplay
3. WMS.addWindow
   - getDisplayContentOrCreate 获取Display
   - WindowState win = new WindowState
   - win.attach(mWindowMap.put(client.asBinder(), win))
   -  mSession.windowAddedLocked
   - new SurfaceSession
   - new SurfaceComposerClient
   - IGraphicBufferProducer





#### 2.2  WindowState implements WindowManagerPolicy.WindowState

> - 在WMS中，WindowState对象代表一个窗口
> - final Session mSession;*//WMS为客户进程创建的Binder服务对象*
> - final IWindow mClient;*//客户端进程Binder对象，W的引用对象

#### 2.3 Session extends IWindowSession.Stub



### 3. DecorView是什么？

在PhoneWindow类中，mDecor的类型是DecorView，当调用setContentView时，如果mDecor还没有创建，则会调用installDecor方法来创建Activity中的DecorView和其他框架的View



#### 3.1 Activity.setContentView

#### 3.2 PhoneWindow.setContentView

#### 3.3 installDecor

#### 3.4 generateDecor

#### 3.5  class DecorView extends FrameLayout



## 三，窗口的显示次序分析

手机屏幕是以左上角为原点，向右为X轴方向，向下为Y轴方向的一个二维空间。为方便管理窗口显示次序，手机屏幕被扩展为了一个三维空间，多定义了一个Z轴，方向为垂直于屏幕表面指向屏幕外。多个窗口依照其前后顺序排布在这个虚拟的Z轴上，因此窗口的显示次序又被称为Z序（Z order）



- WMS.addWindow 当app添加一个view的时候最终会调用到这里

  - win = new WindowState

    - PhoneWindowManager.getWindowLayerLw  计算mBaseLayer(在WindowManagerPolicy接口实现)

      > WindowManagerPolicy接口里面
      >
      > default int getWindowLayerLw(WindowState win) {
      >
      >   return getWindowLayerFromTypeLw(win.getBaseType(), win.canAddInternalSystemWindow());
      >
      >  }

      - getWindowLayerFromTypeLw  把窗口根据类型分成不同的层

    - PhoneWindowManager.getSubWindowLayerFromTypeLw





## 四，窗口的尺寸计算

1. performTraversals

2. relayoutWindow

3. IWindowSession.relayout

4. WMS.relayoutWindow

5. WindowSurfacePlacer.performSurfacePlacement（计算window的大小、执行动画、更新surface）

6. WindowSurfacePlacer.performSurfacePlacementLoop

7. RootWindowContainer.performSurfacePlacement

8. RootWindowContainer.applySurfaceChangesTransaction

9. DisplayContent.applySurfaceChangesTransaction

10. DisplayContent.performLayout

    - PhoneWindowManager.beginLayoutLw

      > 调用PhoneWindowManager类的成员函数beginLayoutLw来设置屏幕的大小；包括状态栏，导航栏

    - DisplayContent.forAllWindows

      > 调用forAllWindows分别计算父窗口和子窗口的大小
      >
      > mChildren.get(i).forAllWindows(callback, traverseTopToBottom)

      - ToBooleanFunction.apply
      - mPerformLayout 是一个Consumer<WindowState>
      - PhoneWindowManager.layoutWindowLw  计算窗口大小
      - WindowState.computeFrameLw

    



## 五，ConfigarationContainer之间的联系

### RootWindowContainer

#### DisplayContent

- DisplayWindowController
  - ActivityDisplay 
- NonAppWindowContainer壁纸
- TaskStackContainers(TaskStack)
  - TaskStack
    - StackWindowController
      - ActivityStack
    - Task
      - TaskWindowContainerController
        - TaskRecord
      - AppWindowToken
        - AppWindowContainerController
          - ActivityRecord

- AboveAppWindowContainers(statusBar)
- NonMagifiableWindowConatiners(输入法)



## 六，Toast

### 6.1 Toast的内部机制介绍

> 1. `Toast`也是基于`Window`来实现的
> 2. `Toast`具有定时取消功能，系统采用`Handler`实现
> 3. `Toast`内部有两类IPC过程：
>    1. Toast访问NotificationManagerService；
>    2. NotificationManagerService回调`Toast`的`TN`接口

### 6.2 Toast的show()方法原理分析

参考https://blog.csdn.net/feather_wch/article/details/81437056



## 六，Activity启动窗口

### ActivityStarter.startActivityUnchecked

#### 6.1.1 ActivityStack.startActivityLocked

##### 6.1.1.1 ActivityStack.insertTaskAtTop 把TaskRecord插入到mTaskHistory中

##### 6.1.1.2 ActivityRecord.createWindowContainer

- new AppWindowContainerController
  - createAppWindow
    - new AppWindowToken 创建了一个AppWindowToken

##### 6.1.1.3 ActivityRecord.showStartingWindow

- ActivityRecord.showStartingWindow 添加第一个启动的启动Window
  - AppWindowContainerController.addStartingWindow
    - scheduleAddStartingWindow
      - mAddStartingWindow.run
        - SplashScreenStartingData.createStartingSurface
          - PhoneWindowManager.addSplashScreen
            - PhoneWindow win = new PhoneWindow(context) 创建一个PhoneWindow
            - PhoneWindowManager.addSplashscreenContent 填充内容
            - WM.addView  添加到WMS





## 七，常见问题

![WMS](https://s2.loli.net/2022/06/07/cZWaUN5iwlOn9MF.png)



### 1. View是如何被添加到屏幕窗口上

https://juejin.cn/post/7101608284439707662#heading-3



首先系统会创建一个顶层布局容器**DecorView**，**DecorView**是一个ViewGroup容器，继承自**FrameLayout**，是**PhoneWindow**对象持有的一个实例，它是所有业务程序的顶层View，是系统内部进行初始化，当DecorView初始化完成之后，系统会根据应用程序的**主题特性**去加载一个基础容器，比如说NoActionBar或者是DarkActionBar等，不同的主题加载的基础容器是不同的，但是无论如何，这样一个基础容器里面，一定会有一个**com.android.internal.R.id.content**的容器，这个容器是一个**FrameLayout**，开发者通过setContentView设置的xml布局文件，就是解析之后被添加到了FrameLayout中。

> 1. 创建顶层布局容器**DecorView**
> 2. 在顶层布局中加载基础布局**ViewGroup**
> 3. 将**ContentView**添加到基础布局中的**FrameLayout**中



### 2. View的绘制流程

https://juejin.cn/post/7101608284439707662#heading-3



当activity创建之后，在ActivityThread.handleResumeActivity里面会通过wm调用addview方法，这个wm我们要找到它的实现类WindowManagerImpl，第一个参数就是我们的顶层Dercorview，第二个参数layoutParams就是顶层Dercorview的布局参数，接着会调用WindowManagerGlobal.addView方法，他在其中会创建出viewroot页面对象，最后调用setview方法将Dercorview和布局属性做一个关联，关联成功之后，准备开始绘制，而绘制开始是调用-->ViewRootImpl.requestLayout() -->scheduleTraversals() -->doTraversal() -->performTraversals()，而真正实现绘制三大步的是在performTraversals里面，第一个就是测量performMeasure，第二个布局performLayout，第三个绘制performDraw



### 3. Window是什么？

1. 表示一个窗口的概念，是所有View的直接管理者，任何视图都通过Window呈现(点击事件由Window->DecorView->View; Activity的setContentView底层通过Window完成)
2. Window是一个抽象类，具体实现是PhoneWindow
3. 创建Window需要通过WindowManager创建
4. WindowManager是外界访问Window的入口
5. Window具体实现位于WindowManagerService中
6. WindowManager和WindowManagerService的交互是通过IPC完成



### 4. Window的内部机制

1. Window和View通过ViewRootImpl建立联系

2. Window并不是实际存在的，而是以View的形式存在

3. WindowManager的三个接口方法也是针对View的

4. 实际使用中无法直接访问Window，必须通过WindowManager

5. View是视图的呈现方式，但是不能单独存在，必须依附在Window这个抽象的概念上

6. WMS把所有的用户消息发给View/ViewGroup，但是在View/ViewGroup处理消息的过程中，有一些操作是公共的, Window把这些公共行为抽象出来, 这就是Window。

   

### 5. WindowSession的作用

> 1. 表示一个Active Client Session
> 2. 每个进程一般都有一个Session对象
> 3. 用于WindowManager交互





### 6. Token

#### 6.1 Token是什么？

> 1. 类型为IBinder，是一个Binder对象。
> 2. 主要分两种Token：
>    1. 指向Window的token: 主要是实现WmS和应用所在进程通信。
>    2. 指向ActivityRecord的token: 主要是实现WmS和AmS通信的。

#### 6.2 Token使用场景？

> 1. Popupwindow的showAtLocation第一个参数需要传入View，这个View就是用来获取Token的。
> 2. Android 5.0新增空间SnackBar同理也需要一个View来获取Token

#### 6.3 Activity中的Token

> 1. ActivityRecord是AmS中用来保存一个Activity信息的辅助类。
> 2. AMS中需要根据Token去找到对应的ActivityRecord。



### 7. 为什么Dialog不能用Application的Context？

> 1. Dialog本身的Token为null，在初始化时如果是使用Application或者Service的Context，在获取到WindowManager时，获取到的token依然是null。
> 2. Dialog如果采用Activity的Context，获取到的WindowManager是在activity.attach()方法中创建，token指向了activity的token。
> 3. 因为通过Application和Service的Context将无法获取到Token从而导致失败。



### 8. ViewRoot是什么

ViewRoot对应ViewRootImpl类，它是连接WMS和DecorView的纽带，但它却并不属于View树的一份子，并不是View的子类也不是View的父类，但它实现了ViewParent接口，所以可以作为名义上的View的父视图。

WindowManager.addView()内部实际是由WindowManagerGlobal完成的，WindowManagerGlobal中有三个列表，一个是保存View的mViews列表，一个是保存ViewRootImpl的mRoots列表，一个是保存WindowManager.LayoutParams的mParams列表，WindowManager每一次addView()都会创建一个对应的ViewRootImpl，在调用ViewRoot.setView后将decorView交给ViewRootImpl。ViewRootImpl中调用performTraversals方法，然后便开始测量布局绘画了，界面才得以显示出来，这就是View的绘制流程起点。



### 9. Dialog的Window创建过程

- 创建Window——同样是通过PolicyManager的makeNewWindow方法完成，与Activity创建过程一致
- 初始化DecorView并将Dialog的视图添加到DecorView中——和Activity一致(setContentView)
- 将DecorView添加到Window中并显示——在Dialog的show方法中，通过WindowManager将DecorView添加到Window中(mWindowManager.addView(mDecor, 1))
- Dialog关闭时会通过WindowManager来移除DecorView：mWindowManager.removeViewImmediate(mDecor)
- Dialog必须采用Activity的Context，因为有应用token(Application的Context没有应用token)，也可以将Dialog的Window通过type设置为系统Window(SYSTEM_ALERT,需要申请权限)就不再需要token。





### 10. Activity、PhoneWindow、DecorView、ViewRootImpl 的关系？

- **PhoneWindow** 其实是 Window 的唯一子类，是 Activity 和 View 交互系统的中间层，用来管理View的，并且在Window创建（添加）的时候就新建了**ViewRootImpl**实例。
- **DecorView** 是整个 View 层级的最顶层，**ViewRootImpl**是DecorView 的**parent**，但是他并不是一个真正的 View，只是继承了ViewParent接口，用来掌管View的各种事件，包括requestLayout、invalidate、dispatchInputEvent 等等。

### 11. WMS的创建在哪一个线程

WMS的创建不是在system_server主线程，而是在另一个线程（DisplayThread）中创建



### 12. Window的addView过程

参考https://blog.csdn.net/feather_wch/article/details/81437056



> 1. WindowManager是一个接口，真正实现类是WindowManagerImpl，并最终以代理模式交给WindowManagerGlobal实现。
> 2. addView: 1-创建ViewRootImpl；2-将ViewRoor、DecorView、布局参数保存到WM的内部列表中；3-ViewRoot.setView()建立ViewRoot和DecorView的联系。
> 3. setView：1-进行View绘制三大流程；2-会通过WindowSession完成Window的添加过程(一次IPC调用)
> 4. requestLayout：内部调用scheduleTraversals(), 底层通过mChoreographer去监听下一帧的刷新信号
> 5. mWindowSession.addToDisplay: 执行WindowManangerService的addWindow
> 6. addWindow: 检查参数等设置;检查Token;将Token、Window保存到WMS中;将WindowState保存到Session中。
>    





### 13. Window的remove过程

参考https://blog.csdn.net/feather_wch/article/details/81437056

> 1. WindowManager中提供了两种删除接口：removeView异步删除、removeViewImmediate同步删除(不建议使用)
> 2. 调用WMGlobal的removeView
> 3. 调用到WMGlobal的removeViewLocked进行真正的移除
> 4. 执行ViewRoot的die方法(): 1-同步方法直接调用doDie 2-异步方法直接发送Message
> 5. doDie(): 调用dispatchDetachedFromWindow()和WindowManagerGlobal.getInstance().doRemoveView(this)
> 6. dispatchDetachedFromWindow: 1-回调onDetachedFromeWindow；2-垃圾回收相关操作；3-通过Session的remove()在WMS中删除Window；4-通过Choreographer移除监听器
>
> 



### 14. Window的更新过程updateViewLayout

参考https://blog.csdn.net/feather_wch/article/details/81437056

> 1. 和添加删除类似，最终调用WindowManagerGlobal的updateViewLayout方法
> 2. root.setLayoutParams会对View进行重新布局——测量、布局、重绘
> 3. root.setLayoutParams还会通过WindowSession更新Window的视图——最终通过WindowManagerService的relayoutWindow()实现(IPC)



### 15. PolicyManager

> 1. 是一个策略类
> 2. Activity的`Window`就是通过`PolicyManager`的一个工厂方法创建
> 3. `PolicyManager`实现的工厂方法全部在策略接口`IPolicy`中声明
> 4. `PolicyManager`的实现类是`Policy`类