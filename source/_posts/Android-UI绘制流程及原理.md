---
title: Android UI绘制流程及原理
date: 2019-08-07 15:03:22
tags:
  - Android
  - 安卓  
  - 源码
---

## 源码讲解

```
public class MainActivity extends Activity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
    }
}

```

我们加载view的时候会在onCreate()调用setContentView()传入布局资源ID,我们点进去这个方法，看看我们的view是怎么被投放在屏幕窗口上的。


```
/**
     * Set the activity content from a layout resource.  The resource will be
     * inflated, adding all top-level views to the activity.
     *
     * @param layoutResID Resource ID to be inflated.
     *
     * @see #setContentView(android.view.View)
     * @see #setContentView(android.view.View, android.view.ViewGroup.LayoutParams)
     */
    public void setContentView(@LayoutRes int layoutResID) {
        getWindow().setContentView(layoutResID);
        initWindowDecorActionBar();
    }
```
<!--more-->
我们发现它是通过getWindow()调用它的setContentView方法，此时，我们需要了解一下getWindow()它是什么。


```
 /**
     * Retrieve the current {@link android.view.Window} for the activity.
     * This can be used to directly access parts of the Window API that
     * are not available through Activity/Screen.
     *
     * @return Window The current window, or null if the activity is not
     *         visual.
     */
    public Window getWindow() {
        return mWindow;
    }
```

我们点进来，发现他直接放回一个mWindow对象，它的类型是Window，那我们了解一下这个Window是什么。点进去Window这个类。


```

/**
 * Abstract base class for a top-level window look and behavior policy.  An
 * instance of this class should be used as the top-level view added to the
 * window manager. It provides standard UI policies such as a background, title
 * area, default key processing, etc.
 *
 * <p>The only existing implementation of this abstract class is
 * android.view.PhoneWindow, which you should instantiate when needing a
 * Window.
 */
public abstract class Window {
}
```

我们看到英语注释，仅存有唯一的实现抽象类的子类就是PhoneWindow，我们查看PhoneWindow这个类的setContentView方法


```

    @Override
    public void setContentView(int layoutResID) {
        // Note: FEATURE_CONTENT_TRANSITIONS may be set in the process of installing the window
        // decor, when theme attributes and the like are crystalized. Do not check the feature
        // before this happens.
        if (mContentParent == null) {
            installDecor();
        } else if (!hasFeature(FEATURE_CONTENT_TRANSITIONS)) {
            mContentParent.removeAllViews();
        }

        if (hasFeature(FEATURE_CONTENT_TRANSITIONS)) {
            final Scene newScene = Scene.getSceneForLayout(mContentParent, layoutResID,
                    getContext());
            transitionTo(newScene);
        } else {
            mLayoutInflater.inflate(layoutResID, mContentParent);
        }
        mContentParent.requestApplyInsets();
        final Callback cb = getCallback();
        if (cb != null && !isDestroyed()) {
            cb.onContentChanged();
        }
        mContentParentExplicitlySet = true;
    }
```

我们发现这个方法主要做了两件事情，调用了一个 installDecor()方法，第二个就是通过
LayoutInflater.inflate()方法去解析我们的当前传入的布局资源id。

#### 1. installDecor方法


```
 if (mDecor == null) {
            mDecor = generateDecor(-1);
            mDecor.setDescendantFocusability(ViewGroup.FOCUS_AFTER_DESCENDANTS);
            mDecor.setIsRootNamespace(true);
            if (!mInvalidatePanelMenuPosted && mInvalidatePanelMenuFeatures != 0) {
                mDecor.postOnAnimation(mInvalidatePanelMenuRunnable);
            }
        } else {
            mDecor.setWindow(this);
        }
```

首先创建DecorView对象，我们点进去看一下怎么创建DecorView对象，点进去generateDecor(-1)方法，

```
protected DecorView generateDecor(int featureId) {
        // System process doesn't have application context and in that case we need to directly use
        // the context we have. Otherwise we want the application context, so we don't cling to the
        // activity.
        Context context;
        if (mUseDecorContext) {
            Context applicationContext = getContext().getApplicationContext();
            if (applicationContext == null) {
                context = getContext();
            } else {
                context = new DecorContext(applicationContext, getContext());
                if (mTheme != -1) {
                    context.setTheme(mTheme);
                }
            }
        } else {
            context = getContext();
        }
        return new DecorView(context, featureId, this, getAttributes());
    }
```

重点看DecorView对象生成的构造方法，随后点进去DecorView，我们首先看一下DecorView是什么，DecorView是继承于FrameLayout，也就是说，它是一个容器，也就是说它在我们布局资源加载首先创建一个DecorView的对象，


```
 DecorView(Context context, int featureId, PhoneWindow window,
            WindowManager.LayoutParams params) {
        super(context);
        mFeatureId = featureId;

        mShowInterpolator = AnimationUtils.loadInterpolator(context,
                android.R.interpolator.linear_out_slow_in);
        mHideInterpolator = AnimationUtils.loadInterpolator(context,
                android.R.interpolator.fast_out_linear_in);

        mBarEnterExitDuration = context.getResources().getInteger(
                R.integer.dock_enter_exit_duration);
        mForceWindowDrawsStatusBarBackground = context.getResources().getBoolean(
                R.bool.config_forceWindowDrawsStatusBarBackground)
                && context.getApplicationInfo().targetSdkVersion >= N;
        mSemiTransparentStatusBarColor = context.getResources().getColor(
                R.color.system_bar_background_semi_transparent, null /* theme */);

        updateAvailableWidth();

        setWindow(window);

        updateLogTag(params);

        mResizeShadowSize = context.getResources().getDimensionPixelSize(
                R.dimen.resize_shadow_size);
        initResizingPaints();
    }
```

创建完DecorView之后，我们再看一个比较重要的方法generateLayout()方法

```
 if (mContentParent == null) {
            mContentParent = generateLayout(mDecor)
 }
```

点进去generateLayout方法


```
    protected ViewGroup generateLayout(DecorView decor) {
        // Apply data from current theme.

        ...
        
        if (a.getBoolean(R.styleable.Window_windowActionBarOverlay, false)) {
            requestFeature(FEATURE_ACTION_BAR_OVERLAY);
        }

        ...

        if (a.getBoolean(R.styleable.Window_windowFullscreen, false)) {
            setFlags(FLAG_FULLSCREEN, FLAG_FULLSCREEN & (~getForcedWindowFlags()));
        }

        ...
      
        return contentParent;
    }

```
我们发现这个方法比较长，往下看的时候我们发现它里面做的一些事情就是根据我们的系统的主题的属性设置很多的特性，通过requestFeature()方法，包括setFlags()等等这一系列的方法的调用，我们继续往下走,
```
 protected ViewGroup generateLayout(DecorView decor) {
     
       ...
     
       // Inflate the window decor.

        int layoutResource;
        int features = getLocalFeatures();
        // System.out.println("Features: 0x" + Integer.toHexString(features));
        if ((features & (1 << FEATURE_SWIPE_TO_DISMISS)) != 0) {
            layoutResource = R.layout.screen_swipe_dismiss;
            setCloseOnSwipeEnabled(true);
        } else if ((features & ((1 << FEATURE_LEFT_ICON) | (1 << FEATURE_RIGHT_ICON))) != 0) {
            if (mIsFloating) {
                TypedValue res = new TypedValue();
                getContext().getTheme().resolveAttribute(
                        R.attr.dialogTitleIconsDecorLayout, res, true);
                layoutResource = res.resourceId;
            } else {
                layoutResource = R.layout.screen_title_icons;
            }
            // XXX Remove this once action bar supports these features.
            removeFeature(FEATURE_ACTION_BAR);
            // System.out.println("Title Icons!");
        } else if ((features & ((1 << FEATURE_PROGRESS) | (1 << FEATURE_INDETERMINATE_PROGRESS))) != 0
                && (features & (1 << FEATURE_ACTION_BAR)) == 0) {
            // Special case for a window with only a progress bar (and title).
            // XXX Need to have a no-title version of embedded windows.
            layoutResource = R.layout.screen_progress;
            // System.out.println("Progress!");
        } else if ((features & (1 << FEATURE_CUSTOM_TITLE)) != 0) {
            // Special case for a window with a custom title.
            // If the window is floating, we need a dialog layout
            if (mIsFloating) {
                TypedValue res = new TypedValue();
                getContext().getTheme().resolveAttribute(
                        R.attr.dialogCustomTitleDecorLayout, res, true);
                layoutResource = res.resourceId;
            } else {
                layoutResource = R.layout.screen_custom_title;
            }
            // XXX Remove this once action bar supports these features.
            removeFeature(FEATURE_ACTION_BAR);
        } else if ((features & (1 << FEATURE_NO_TITLE)) == 0) {
            // If no other features and not embedded, only need a title.
            // If the window is floating, we need a dialog layout
            if (mIsFloating) {
                TypedValue res = new TypedValue();
                getContext().getTheme().resolveAttribute(
                        R.attr.dialogTitleDecorLayout, res, true);
                layoutResource = res.resourceId;
            } else if ((features & (1 << FEATURE_ACTION_BAR)) != 0) {
                layoutResource = a.getResourceId(
                        R.styleable.Window_windowActionBarFullscreenDecorLayout,
                        R.layout.screen_action_bar);
            } else {
                layoutResource = R.layout.screen_title;
            }
            // System.out.println("Title!");
        } else if ((features & (1 << FEATURE_ACTION_MODE_OVERLAY)) != 0) {
            layoutResource = R.layout.screen_simple_overlay_action_mode;
        } else {
            // Embedded, so no decoration is needed.
            layoutResource = R.layout.screen_simple;
            // System.out.println("Simple!");
        }
        
     ...
 
     
 }
```

通过注释Inflate the window decor.我们知道是解析我们窗口的view，首先他定义了一个layoutResource一个int的值，然后根据features的不同来对layoutResource进行赋值，例如


```
 if ((features & (1 << FEATURE_SWIPE_TO_DISMISS)) != 0) {
            layoutResource = R.layout.screen_swipe_dismiss;
            setCloseOnSwipeEnabled(true);
        }
```

**R.layout.screen_swipe_dismiss**它属于系统源码里面的一个布局资源

当layoutResource通过赋值成功之后，调用onResourcesLoaded方法，如下


```

        mDecor.startChanging();
        mDecor.onResourcesLoaded(mLayoutInflater, layoutResource);

```

那onResourcesLoaded这个方法做了什么事情呢？我们点进去里面看

```
 void onResourcesLoaded(LayoutInflater inflater, int layoutResource) {
        if (mBackdropFrameRenderer != null) {
            loadBackgroundDrawablesIfNeeded();
            mBackdropFrameRenderer.onResourcesLoaded(
                    this, mResizingBackgroundDrawable, mCaptionBackgroundDrawable,
                    mUserCaptionBackgroundDrawable, getCurrentColor(mStatusColorViewState),
                    getCurrentColor(mNavigationColorViewState));
        }

        mDecorCaptionView = createDecorCaptionView(inflater);
        final View root = inflater.inflate(layoutResource, null);
        if (mDecorCaptionView != null) {
            if (mDecorCaptionView.getParent() == null) {
                addView(mDecorCaptionView,
                        new ViewGroup.LayoutParams(MATCH_PARENT, MATCH_PARENT));
            }
            mDecorCaptionView.addView(root,
                    new ViewGroup.MarginLayoutParams(MATCH_PARENT, MATCH_PARENT));
        } else {

            // Put it below the color views.
            addView(root, 0, new ViewGroup.LayoutParams(MATCH_PARENT, MATCH_PARENT));
        }
        mContentRoot = (ViewGroup) root;
        initializeElevation();
    }

```

我们发现。这个方法里面的操作很简单，首先将layoutResource参数进行解析，创建一个view对象


```
        final View root = inflater.inflate(layoutResource, null);

```

然后，通过addView方法将这个view添加到decorview里面

然后我们回来继续探究generateLayout方法


```
    protected ViewGroup generateLayout(DecorView decor) {

        ...
        
        ViewGroup contentParent = (ViewGroup)findViewById(ID_ANDROID_CONTENT);

        ...
        
        return contentParent;

        ...
        
    }
```


通过findViewById得到一个容器，这个id是一个固定的值


```
/**
     * The ID that the main layout in the XML layout file should have.
     */
    public static final int ID_ANDROID_CONTENT = com.android.internal.R.id.content;
```

通过注释我们知道这个id是主容器她的资源id，而且是一定存在的。


我们的到这个容器contentParent，直接将它返回。

我们用图示来描述上述过程

![image](http://lbz-blog.test.upcdn.net/post/WechatIMG10.png)



#### 2.             mLayoutInflater.inflate(layoutResID, mContentParent);


mContentParent实际上表示的就是上图的FrameLayout,它的id就是@android:id/content

layoutResID就是我们MainActivity传入的布局资源id，通过inflate解析之后添加到基础容器中的FrameLayout中



## View是如何被添加到屏幕窗口上
1. 创建顶层布局容器**DecorView**
2. 在顶层布局中加载基础布局**ViewGroup**
3. 将**ContentView**添加到基础布局中的**FrameLayout**中



---

## View的绘制流程
1. 绘制入口

```
ActivityThread.handleResumeActivity
-->WindowManagerImpl.addView(dercorView,layoutParams)
-->WindowManagerGlobal.addView()
```

2. 绘制的类及方法

```
ViewRootImpl.setView(decorView,layoutParams,parentView)
-->ViewRootImpl.requestLayout()
-->scheduleTraversals()
-->doTraversal()
-->performTraversals()

```

3. 绘制三大步骤

```
测量:ViewRootImpl.performMeasure
布局:ViewRootImpl.performLayout
绘制:ViewRootImpl.performDraw
```


当activity创建之后，在ActivityThread.handleResumeActivity里面会通过wm调用addview方法，这个wm我们要找到它的实现类WindowManagerImpl，第一个参数就是我们的顶层Dercorview，第二个参数layoutParams就是顶层Dercorview的布局参数，接着会调用WindowManagerGlobal.addView方法，他在其中会创建出viewroot页面对象，最后调用setview方法将Dercorview和布局属性做一个关联，关联成功之后，准备开始绘制，而绘制开始是调用-->ViewRootImpl.requestLayout()
-->scheduleTraversals()
-->doTraversal()
-->performTraversals()，而真正实现绘制三大步的是在performTraversals里面，第一个就是测量performMeasure，第二个布局performLayout，第三个绘制performDraw



#### 源码解析


首先打开ActivityThread这个类，找到handleMessage这个方法 ，这个方法是主线程里面处理消息，我们要找到一个名为H的类,他是Handler的子类




我们看一下handleResumeActivity这个方法
```
  @Override
    public void handleResumeActivity(IBinder token, boolean finalStateRequest, boolean isForward,
            String reason) {
  
        ...

        // TODO Push resumeArgs into the activity for consideration
        final ActivityClientRecord r = performResumeActivity(token, finalStateRequest, reason);
        
        ...
        
    }


```


首先

```
final ActivityClientRecord r = performResumeActivity(token, finalStateRequest, reason);

```
这个步骤回调的就是activity生命周期中的OnResume方法，我们接下去往下看


```
     @Override
    public void handleResumeActivity(IBinder token, boolean finalStateRequest, boolean isForward,
            String reason) {
     
     ...
     
     if (r.window == null && !a.mFinished && willBeVisible) {
            r.window = r.activity.getWindow();
            View decor = r.window.getDecorView();
            decor.setVisibility(View.INVISIBLE);
            ViewManager wm = a.getWindowManager();
            WindowManager.LayoutParams l = r.window.getAttributes();
            a.mDecor = decor;
            l.type = WindowManager.LayoutParams.TYPE_BASE_APPLICATION;
            l.softInputMode |= forwardBit;
            if (r.mPreserveWindow) {
                a.mWindowAdded = true;
                r.mPreserveWindow = false;
                // Normally the ViewRoot sets up callbacks with the Activity
                // in addView->ViewRootImpl#setView. If we are instead reusing
                // the decor view we have to notify the view root that the
                // callbacks may have changed.
                ViewRootImpl impl = decor.getViewRootImpl();
                if (impl != null) {
                    impl.notifyChildRebuilt();
                }
            }
            if (a.mVisibleFromClient) {
                if (!a.mWindowAdded) {
                    a.mWindowAdded = true;
                    wm.addView(decor, l);
                } else {
                    // The activity will get a callback for this {@link LayoutParams} change
                    // earlier. However, at that time the decor will not be set (this is set
                    // in this method), so no action will be taken. This call ensures the
                    // callback occurs with the decor set.
                    a.onWindowAttributesChanged(l);
                }
            }

            // If the window has already been added, but during resume
            // we started another activity, then don't yet make the
            // window visible.
        } else if (!willBeVisible) {
            if (localLOGV) Slog.v(TAG, "Launch " + r + " mStartedActivity set");
            r.hideForNow = true;
        }
        
        ...
        
    }

```

我们看到初始化了一个 WindowManager.LayoutParams对象，也就是窗口布局属性对象，然后再调用了一个wm.addView(decor, l);

我们看一下这个wm是什么？我们点进去，他是一个接口


```
public interface ViewManager
{
    /**
     * Assign the passed LayoutParams to the passed View and add the view to the window.
     * <p>Throws {@link android.view.WindowManager.BadTokenException} for certain programming
     * errors, such as adding a second view to a window without removing the first view.
     * <p>Throws {@link android.view.WindowManager.InvalidDisplayException} if the window is on a
     * secondary {@link Display} and the specified display can't be found
     * (see {@link android.app.Presentation}).
     * @param view The view to be added to this window.
     * @param params The LayoutParams to assign to view.
     */
    public void addView(View view, ViewGroup.LayoutParams params);
    public void updateViewLayout(View view, ViewGroup.LayoutParams params);
    public void removeView(View view);
}

```

我们找一下他对应的实现


```
 ViewManager wm = a.getWindowManager();
```

点进去getWindowManager方法，看到在Activity类中返回的是WindowManager这个对象，接下来看一下这个WindowManager是在哪里实现的，我们在Activity类中的attach方法中找到WindowManager的赋值处理


```
 final void attach(Context context, ActivityThread aThread,
            Instrumentation instr, IBinder token, int ident,
            Application application, Intent intent, ActivityInfo info,
            CharSequence title, Activity parent, String id,
            NonConfigurationInstances lastNonConfigurationInstances,
            Configuration config, String referrer, IVoiceInteractor voiceInteractor,
            Window window, ActivityConfigCallback activityConfigCallback) {
               
            ...
                    
                    mWindowManager = mWindow.getWindowManager();

            ...    
                
            }
```

mWindowManager看一下还和谁有关联


```
 public void setWindowManager(WindowManager wm, IBinder appToken, String appName,
            boolean hardwareAccelerated) {
        mAppToken = appToken;
        mAppName = appName;
        mHardwareAccelerated = hardwareAccelerated
                || SystemProperties.getBoolean(PROPERTY_HARDWARE_UI, false);
        if (wm == null) {
            wm = (WindowManager)mContext.getSystemService(Context.WINDOW_SERVICE);
        }
        mWindowManager = ((WindowManagerImpl)wm).createLocalWindowManager(this);
    }

```


看最后一行，mWindowManager的实例化，我们就要去WindowManagerImpl里面去找

找什么呢？

我们应该要在WindowManagerImpl找wm.addView()方法。


```
@Override
    public void addView(@NonNull View view, @NonNull ViewGroup.LayoutParams params) {
        applyDefaultToken(params);
        mGlobal.addView(view, params, mContext.getDisplay(), mParentWindow);
    }
```


看到他方法里面又通过mGlobal这个对象调用了addView方法,我们继续看一下这个mGlobal是什么


```
    private final WindowManagerGlobal mGlobal = WindowManagerGlobal.getInstance();

```

我们再看一下WindowManagerGlobal是什么,点进去WindowManagerGlobal找到addview方法


```

 public void addView(View view, ViewGroup.LayoutParams params,Display display, Window parentWindow) {
  
  ...
  
    ViewRootImpl root;
    View panelParentView = null;
  
  ...
  
   root = new ViewRootImpl(view.getContext(), display);

    view.setLayoutParams(wparams);
    mViews.add(view);
    mRoots.add(root);
    mParams.add(wparams);
  
   // do this last because it fires off messages to start doing things
            try {
                root.setView(view, wparams, panelParentView);
            } catch (RuntimeException e) {
                // BadTokenException or InvalidDisplayException, clean up.
                if (index >= 0) {
                    removeViewLocked(index, true);
                }
                throw e;
            }
  ...
  
 }


```

我们看到最后调用了一个setView方法，我们点进去
它里面有一个requestLayout()方法

```
 // Schedule the first layout -before- adding to the window
                // manager, to make sure we do the relayout before receiving
                // any other events from the system.
                requestLayout();
```

点进去发现


```
  @Override
    public void requestLayout() {
        if (!mHandlingLayoutInLayoutRequest) {
            checkThread();
            mLayoutRequested = true;
            scheduleTraversals();
        }
    }
```

它里面执行checkThread()方法，这个方法表现的是我们当前绘制线程是否在主线程中进行，scheduleTraversals点进去


```
void scheduleTraversals() {
        if (!mTraversalScheduled) {
            mTraversalScheduled = true;
            mTraversalBarrier = mHandler.getLooper().getQueue().postSyncBarrier();
            mChoreographer.postCallback(
                    Choreographer.CALLBACK_TRAVERSAL, mTraversalRunnable, null);
            if (!mUnbufferedInputDispatch) {
                scheduleConsumeBatchedInput();
            }
            notifyRendererOfFramePending();
            pokeDrawLockIfNeeded();
        }
    }
```


通过mChoreographer的postCallback方法，传入了一个mTraversalRunnable。究竟这个mTraversalRunnable是什么呢，点进去
TraversalRunnable，它是一个runnable，看run方法doTraversalwith ()方法，然后再看里面的performTraversals()方法。这个方法里面执行的就是绘制流程的三大步。





```
    private void performTraversals() {

    ...
    
    
    // Ask host how big it wants to be
    performMeasure(childWidthMeasureSpec, childHeightMeasureSpec);
    
    ...
    
    performLayout(lp, mWidth, mHeight);

    ...
    
    performDraw();

    ...
        
    }


```



我们总结以上流程

![image](http://lbz-blog.test.upcdn.net/post/1565089820898.jpg)










