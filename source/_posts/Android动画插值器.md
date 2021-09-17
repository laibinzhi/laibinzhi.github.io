---
title: Android动画插值器Interpolator
date: 2021-09-16 18:23:47
tags:
  - Android
  - 动画
---

### 前言
#### Android常见的三种动画
##### 视图动画之帧动画
帧动画是顺序播放一组预先定义好的图片，类似于电影播放。不同于View动画，系统提供了另外一个类AnimationDrawable来使用帧动画。帧动画的使用比较简单，首先需要通过XML来定义一个AnimationDrawable


```
    // res/drawable/frame_animation.xml
    <? xml version="1.0" encoding="utf-8"? >
    <animation-list xmlns:android="http://schemas.android.com/apk/res/android"
        android:oneshot="false">
        <item android:drawable="@drawable/image1" android:duration="500" />
        <item android:drawable="@drawable/image2" android:duration="500" />
        <item android:drawable="@drawable/image3" android:duration="500" />
    </animation-list>
```
<!--more-->
然后将上述的Drawable作为View的背景并通过Drawable来播放动画即可：

```
    Button mButton = (Button)findViewById(R.id.button1);
    mButton.setBackgroundResource(R.drawable.frame_animation);
    AnimationDrawable drawable = (AnimationDrawable) mButton.getBackground();
    drawable.start();
```
帧动画的使用比较简单，但是比较容易引起OOM，所以在使用帧动画时应尽量避免使用过多尺寸较大的图片。

##### 视图动画之补间动画
tween 动画也叫作补间动画，它可以在一定的时间内使 View 完成四种基本的动画，即平移、缩放、透明度、旋转，也可以将它们组合到一起播放出来。这里先提一下未来会研究的属性动画，值得注意的是，无论是帧动画还是补间动画，都是把动画效果作用到 View 上，如果一个不是View的元素想实现动画，那这两种就无能为力了，只能请属性动画帮忙了。并且补间动画仅仅是给View增加了动画的“假象”，比如一个按钮从左侧跑到了右侧，你在右侧是无法点击它的，但是这不代表补间动画就没有用武之地了，当你需要的动画效果无外乎上面那四种动画，并且仅仅是展示的时候，补间动画就再合适不过了。同样，补间动画的实现依然可以有两种方式，xml定义或者是纯代码的方式，这里依然是建议使用 xml 的方式。


```
 // res/anim/alpha_anim.xml
<alpha xmlns:android="http://schemas.android.com/apk/res/android"
    android:duration="200"
    android:fillAfter="true"
    android:fromAlpha="0"
    android:interpolator="@android:anim/linear_interpolator"
    android:repeatCount="-1"
    android:repeatMode="reverse"
    android:shareInterpolator="false"
    android:toAlpha="1">
</alpha>
```

```
Animation alpha = AnimationUtils.loadAnimation(this, R.anim.alpha_anim);
ivFrame.startAnimation(alpha);
```

##### 属性动画

属性动画系统是一个强健的框架，用于为几乎任何内容添加动画效果。您可以定义一个随时间更改任何对象属性的动画，无论其是否绘制到屏幕上。属性动画会在指定时长内更改属性（对象中的字段）的值。要添加动画效果，请指定要添加动画效果的对象属性，例如对象在屏幕上的位置、动画效果持续多长时间以及要在哪些值之间添加动画效果。

##### 属性动画与视图动画的区别
视图动画系统仅提供为 View 对象添加动画效果的功能，因此，如果您想为非 对象添加动画效果，则必须实现自己的代码才能做到。视图动画系统也存在一些限制，因为它仅公开 对象的部分方面来供您添加动画效果；例如，您可以对视图的缩放和旋转添加动画效果，但无法对背景颜色这样做。

视图动画系统的另一个缺点是它只会在绘制视图的位置进行修改，而不会修改实际的视图本身。例如，如果您为某个按钮添加了动画效果，使其可以在屏幕上移动，该按钮会正确绘制，但能够点击按钮的实际位置并不会更改，因此您必须通过实现自己的逻辑来处理此事件。

有了属性动画系统，您就可以完全摆脱这些束缚，还可以为任何对象（视图和非视图）的任何属性添加动画效果，并且实际修改的是对象本身。属性动画系统在执行动画方面也更为强健。概括地讲，您可以为要添加动画效果的属性（例如颜色、位置或大小）分配 Animator，还可以定义动画的各个方面，例如多个 Animator 的插值和同步。

不过，视图动画系统的设置需要的时间较短，需要编写的代码也较少。如果视图动画可以完成您需要执行的所有操作，或者现有代码已按照您需要的方式运行，则无需使用属性动画系统。在某些用例中，也可以针对不同的情况同时使用这两种动画系统。

### 正文
#### 什么是插值器
插值器指定了如何根据时间计算动画中的特定值。例如，您可以指定动画在整个动画中以线性方式播放，即动画在整个播放期间匀速移动；也可以指定动画使用非线性时间，例如动画在开始后加速并在结束前减速。

通俗易懂的说，Interpolator负责控制动画变化的速率，使得基本的动画效果能够以匀速、加速、减速、抛物线速率等各种速率变化。 
动画是开发者给定开始和结束的“关键帧”，其变化的“中间帧”是有系统计算决定然后播放出来。因此，动画的每一帧都将在开始和结束之间的特定时间显示。此时动画时间被转换为时间索引，则动画时间轴上的每个点都可以转换成0.0到1.0之间的一个浮点数。然后再将该值用于计算该对象的属性变换。在变换的情况下，y轴上，0.0对应于起始位置，1.0对应于结束位置，0.5对应于起始和结束之间的中间，对于一些插值器其值还可以是0~1之外的数值。

比如：对于LinearInterpolator（线性插值器）的平移动画来讲，在0.3这个时间点视图则刚好移动了整个动画的30%。

Interpolator 本质上是一个数学函数，其取数字在0.0和1.0之间，并将其转换为另一个数字。

#### 应用场景

补间动画和属性动画

#### 具体使用

##### 设置方式
- xml
  
```
<?xml version="1.0" encoding="utf-8"?>
<scale xmlns:android="http://schemas.android.com/apk/res/android"
    android:interpolator="@android:anim/overshoot_interpolator"
    // 通过资源ID设置插值器
    android:duration="3000"
    android:fromXScale="0.0"
    android:fromYScale="0.0"
    android:pivotX="50%"
    android:pivotY="50%"
    android:toXScale="2"
    android:toYScale="2" />
————————————————
```
- 代码
  
```
   ObjectAnimator  animatorOut = ObjectAnimator.ofFloat(followLayout, View.TRANSLATION_X,
                startX, endX);
    animatorOut.setDuration(500);
    animatorOut.setInterpolator(new AccelerateInterpolator());
    animatorOut.addListener(new AnimatorListenerAdapter() {
            @Override
            public void onAnimationEnd(Animator animation) {
            }
    });
    animatorOut.start();
```


##### 系统内置的插值器
- LinearInterpolator

Resource id: @android:anim/linear_interpolator

Formula: y=t

匀速。以常量速率改变。y=x

![image](http://lbz-blog.test.upcdn.net/post/android%20animation%20interpolator/LinearInterpolator.gif)

- LinearOutSlowInInterpolator

持续减速。

它和 DecelerateInterpolator比起来，同为减速曲线，主要区别在于 LinearOutSlowInInterpolator的初始速度更高。对于人眼的实际感觉，区别其实也不大，不过还是能看出来一些的。

![image](http://lbz-blog.test.upcdn.net/post/android%20animation%20interpolator/LinearOutSlowInInterpolator.gif)

- AccelerateInterpolator

Resource id: @android:anim/accelerate_interpolator

Formula: y=t2f

持续加速，在整个动画过程中，一直在加速，直到动画结束的一瞬间，直接停止。
它主要用在离场效果中，比如某个物体从界面中飞离，就可以用这种效果。到了最后动画骤停的时候，物体已经飞出用户视野，看不到了，所以他们是并不会察觉到这个骤停的。

![image](http://lbz-blog.test.upcdn.net/post/android%20animation%20interpolator/AccelerateInterpolator.gif)

- DecelerateInterpolator

Resource id: @android:anim/decelerate_interpolator

Formula: y=1–(1–t)2f

持续减速直到 0。

动画开始的时候是最高速度，然后在动画过程中逐渐减速，直到动画结束的时候恰好减速到 0。

它的效果和 AccelerateInterpolator相反，适用场景也和它相反：它主要用于入场效果，比如某个物体从界面的外部飞入界面后停在某处。

![image](http://lbz-blog.test.upcdn.net/post/android%20animation%20interpolator/DecelerateInterpolator.gif)

- AccelerateDecelerateInterpolator

Resource id: @android:anim/accelerate_decelerate_interpolator

Formula: y=cos((t+1)π)/2+0.5

先加速再减速。这是**默认**的Interpolator，也就是说如果你不设置的话，那么动画将会使用这个Interpolator。它的动画效果看起来就像是物体从速度为0开始逐渐加速，然后再逐渐减速直到 0 的运动。它的速度 / 时间曲线以及动画完成度 / 时间曲线都是一条正弦 / 余弦曲线

![image](http://lbz-blog.test.upcdn.net/post/android%20animation%20interpolator/AccelerateDecelerateInterpolator.gif)

- OvershootInterpolator

Resource id: @android:anim/overshoot_interpolator

Formula: y=(T+1)×(t−1)3+T×(t−1)2+1

动画会超过目标值一些，然后再弹回来。效果看起来有点像你一屁股坐在沙发上后又被弹起来一点的感觉。

![image](http://lbz-blog.test.upcdn.net/post/android%20animation%20interpolator/OvershootInterpolator.gif)

- AnticipateInterpolator

Resource id: @android:anim/anticipate_interpolator

Formula: y=(T+1)×t3–T×t2

先回拉一下再进行正常动画轨迹。效果看起来有点像投掷物体或跳跃等动作前的蓄力。

如果是图中这样的平移动画，那么就是位置上的回拉；如果是放大动画，那么就是先缩小一下再放大；其他类型的动画同理。

![image](http://lbz-blog.test.upcdn.net/post/android%20animation%20interpolator/AnticipateInterpolator.gif)

- AnticipateOvershootInterpolator

Resource id: @android:anim/anticipate_overshoot_interpolator


OvershootInterpolator和AnticipateInterpolator的结合版：开始前回拉，最后超过一些然后回弹。


![image](http://lbz-blog.test.upcdn.net/post/android%20animation%20interpolator/AnticipateOvershootInterpolator.gif)

- CycleInterpolator

Resource id: @android:anim/cycle_interpolator

Formula: y=sin(2π×C×t)

正弦 / 余弦曲线，不过它和AccelerateDecelerateInterpolator 的区别是，它可以自定义曲线的周期，所以动画可以不到终点就结束，也可以到达终点后回弹，回弹的次数由曲线的周期决定，曲线的周期由CycleInterpolator()构造方法的参数决定。

![image](http://lbz-blog.test.upcdn.net/post/android%20animation%20interpolator/CycleInterpolator.gif)

- BounceInterpolator

Resource id: @android:anim/bounce_interpolator

这个内插器就像一个球，上下弹跳直到它停止。有点像玻璃球

![image](http://lbz-blog.test.upcdn.net/post/android%20animation%20interpolator/BounceInterpolator.gif)

- PathInterpolator

自定义动画完成度 / 时间完成度曲线。

用这个 Interpolator 你可以定制出任何你想要的速度模型。定制的方式是使用一个 Path 对象来绘制出你要的动画完成度 / 时间完成度曲线。

![image](http://lbz-blog.test.upcdn.net/post/android%20animation%20interpolator/PathInterpolator.gif)

##### 自定义内插器

根据动画的进度（0%-100%）计算出当前属性值改变的百分比

自定义插值器需要实现 Interpolator / TimeInterpolator接口 & 复写getInterpolation（）

- 补间动画 实现 Interpolator接口
- 属性动画实现TimeInterpolator接口
TimeInterpolator接口是属性动画中新增的，用于兼容Interpolator接口，这使得所有过去的Interpolator实现类都可以直接在属性动画使用


```
public interface TimeInterpolator {

    /**
     * 参数：输入值变化范围是0-1，且随着动画进度（0% - 100% ）均匀变化
     * 即动画开始时，input值=0；动画结束时input=1，而中间的值则是随着动画的进* 度（0% - 100%）在0到1之间均匀增加
     * 返回：用于估值器继续计算的fraction值
     */
    float getInterpolation(float input);
}

```

- 实例

创建一个以全速开始，然后减慢一半然后再次加速到最后的插值器


```
public class HesitateInterpolator implements Interpolator {
  public HesitateInterpolator() {}
  public float getInterpolation(float t) {
    float x=2.0f*t-1.0f;
    return 0.5f*(x*x*x + 1.0f);
  }
}
```

![image](http://lbz-blog.test.upcdn.net/post/android%20animation%20interpolator/HesitateInterpolator.gif)

### 结语

附上项目的代码地址[https://github.com/laibinzhi/AndroidAnimationInterpolator](https://github.com/laibinzhi/AndroidAnimationInterpolator)