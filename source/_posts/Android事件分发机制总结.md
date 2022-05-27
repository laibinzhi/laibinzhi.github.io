---
title: Android事件分发机制总结
date: 2022-05-27 11:12:17
tags:
  - Android
  - 安卓
  - View  
  - 源码
---


# Android事件分发机制总结

## 三个角色

#### Activity

Activity：只有分发**dispatchTouchEvent**和消费**onTouchEvent**两个方法。 事件由ViewRootImpl中DecorView  dispatchTouchEvent分发Touch事件->Activity的dispatchTouchEvent()- DecorView。superDispatchTouchEvent->ViewGroup的dispatchTouchEvent()。 如果返回false直接掉用onTouchEvent，true表示被消费



#### ViewGroup

拥有分发、拦截和消费三个方法。：对应一个根ViewGroup来说，点击事件产生后，首先会传递给它，dispatchTouchEvent就会被调用，如果这个ViewGroup的onInterceptTouchEvent方法返回true就表示它要拦截当前事件， 事件就会交给这个ViewGroup的onTouchEvent处理。如果这个ViewGroup的onInterceptTouchEvent方法返回false就表示它不拦截当前事件，这时当前事件就会继续传递给它的子元素，接着子元素的dispatchTouchEvent方法就会被调用。

<!--more-->



#### View

只有分发和消费两个方法。方法返回值为true表示当前视图可以处理对应的事件；返回值为false表示当前视图不处理这个事件，会被传递给父视图的



## 三个方法

- dispatchTouchEvent()

  > 方法返回值为true表示事件被当前视图消费掉； 返回为false表示 停止往子View传递和
  >
  > 分发,交给父类的onTouchEvent处理

- onInterceptTouchEvent()

  >  return false 表示不拦截，需要继续传递给子视图。return true 拦截这个事件并交
  >
  > 由自身的onTouchEvent方法进行消费. 

-  onTouchEvent()

  >  return false 是不消费事件，会被传递给父视图的onTouchEvent方法进行处理。return true是消费事件。



## 图解

![Android事件分发机制.drawio](https://s2.loli.net/2022/05/27/Ow9hvxfUzrubZB3.png)





![vqpv7u4i1j](https://s2.loli.net/2022/05/27/J3tNiCvkrcEpqP8.png)





### Activity图解

![activity事件分发](https://s2.loli.net/2022/05/27/8ILeCc4yq6g2DVQ.png)



### ViewGroup图解



![viewgroup图解](https://s2.loli.net/2022/05/27/ShkeQB4GWc8NwLa.png)



### View的图解

![view的图解](https://s2.loli.net/2022/05/27/sLM8augAUTGK1R2.png)



## 伪代码演示

### View的事件分发

```java
// 点击事件产生后
// 步骤1：调用dispatchTouchEvent()
public boolean dispatchTouchEvent(MotionEvent ev) {

    boolean consume = false; //代表 是否会消费事件

    // 步骤2：判断是否拦截事件
    if (onInterceptTouchEvent(ev)) {
      // a. 若拦截，则将该事件交给当前View进行处理
      // 即调用onTouchEvent()去处理点击事件
      consume = onTouchEvent (ev) ;

    } else {

      // b. 若不拦截，则将该事件传递到下层
      // 即 下层元素的dispatchTouchEvent()就会被调用，重复上述过程
      // 直到点击事件被最终处理为止
      consume = child.dispatchTouchEvent (ev) ;
    }

    // 步骤3：最终返回通知 该事件是否被消费（接收 & 处理）
    return consume;

}
```



### onTouch，onTouchEvent和onClick

```java
public void consumeEvent(MotionEvent event) {
    if (setOnTouchListener) {
        onTouch();
        if (!onTouch()) {
            onTouchEvent(event);
        }
    } else {
        onTouchEvent(event);
    }

    if (setOnClickListener) {
        onClick();
    }
}
```

onTouch方法是View的 OnTouchListener借口中定义的方法。 当一个View绑定了OnTouchLister后，当有touch事件触发时，就会调用onTouch方 onTouchEvent 处理点击事件在dispatchTouchEvent中掉用onTouchListener的onTouch方法优先级比onTouchEvent高，会先触发。 假如onTouch方法返回false，会接着触发onTouchEvent，反之onTouchEvent方法不会被调用。 内置诸如click事件的实现等等都基于onTouchEvent，假如onTouch返回true，这些事件将不会被触发。

**总结如下：**

**dispatchTouchEvent > mOnTouchListener.onTouch() > onTouchEvent >onClick**



## View事件冲突

#### 外部拦截法

外部拦截法：指点击事件都先经过父容器的拦截处理，如果父容器需要此事件就拦截，否则就不拦截。具体方法：需要重写父容器的**onInterceptTouchEvent**方法，在内部做出相应的拦截。

> 父View在ACTION_MOVE中开始拦截事件，那么后续ACTION_UP也将默认交给父View处理

```java
//在ACTION_MOVE方法中进行判断，如果需要父View处理则返回true，否则返回false，事件分发给子View去处理。    
public boolean onInterceptTouchEvent(MotionEvent event) {
        boolean intercepted = false;
        int x = (int) event.getX();
        int y = (int) event.getY();
        switch (event.getAction()) {
            case MotionEvent.ACTION_DOWN: {
              //ACTION_DOWN 一定返回false，不要拦截它，否则根据View事件分发机制，后续ACTION_MOVE 与 ACTION_UP事件都将默认交给父View去处理！
                intercepted = false;
                break;
            }
            case MotionEvent.ACTION_MOVE: {
                if (满足父容器的拦截要求) {
                    intercepted = true;
                } else {
                    intercepted = false;
                }
                break;
            }
            //原则上ACTION_UP也需要返回false，如果返回true，并且滑动事件交给子View处理，那么子View将接收不到ACTION_UP事件，子View的onClick事件也无法触发。而父View不一样，如果父View在ACTION_MOVE中开始拦截事件，那么后续ACTION_UP也将默认交给父View处理！
            case MotionEvent.ACTION_UP: {
                intercepted = false;
                break;
            }
            default:
                break;
        }
        mLastXIntercept = x;
        mLastYIntercept = y;
        return intercepted;
    }
```



#### 内部拦截法

 内部拦截法：指父容器不拦截任何事件，而将所有的事件都传递给子容器，如果子容器需要此事件就直接消耗，否则就交由父容器进行处理。具体方法：需要配合**requestDisallowInterceptTouchEvent**方法。

```java
    public boolean dispatchTouchEvent(MotionEvent event) {
        int x = (int) event.getX();
        int y = (int) event.getY();

        switch (event.getAction()) {
            //内部拦截法要求父View不能拦截ACTION_DOWN事件，由于ACTION_DOWN不受FLAG_DISALLOW_INTERCEPT标志位控制，一旦父容器拦截ACTION_DOWN那么所有的事件都不会传递给子View。
            case MotionEvent.ACTION_DOWN: {
                parent.requestDisallowInterceptTouchEvent(true);
                break;
            }
            //滑动策略的逻辑放在子View的dispatchTouchEvent方法的ACTION_MOVE中，如果父容器需要获取点击事件则调用 parent.requestDisallowInterceptTouchEvent(false)方法，让父容器去拦截事件。
            case MotionEvent.ACTION_MOVE: {
                int deltaX = x - mLastX;
                int deltaY = y - mLastY;
                if (父容器需要此类点击事件) {
                    parent.requestDisallowInterceptTouchEvent(false);
                }
                break;
            }
            case MotionEvent.ACTION_UP: {
                break;
            }
            default:
                break;
        }

        mLastX = x;
        mLastY = y;
        return super.dispatchTouchEvent(event);
    }
```



#### 具体思路

- 滑动方向不一致

  > **我们可以根据当前滑动方向，水平还是垂直来判断这个事件到底该交给谁来处理。**至于如何获得滑动方向，我们可以得到滑动过程中的两个点的坐标。一般情况下根据水平和竖直方向滑动的距离差就可以判断方向，当然也可以根据滑动路径形成的夹角（或者说是斜率如下图）、水平和竖直方向滑动速度差来判断。

- 滑动方向一致

  > 根据业务

## 常见问题

#### 1. View的事件分发机制

- 事件都是从Activity.dispatchTouchEvent()开始传递
- 一个事件发生后，首先传递给Activity，然后一层一层往下传，从上往下调用dispatchTouchEvent方法传递事件：
   `activity --> ~~ --> ViewGroup --> View`
- 如果事件传递给最下层的View还没有被消费，就会按照反方向回传给Activity，从下往上调用onTouchEvent方法，最后会到Activity的onTouchEvent()函数，如果Activity也没有消费处理事件，这个事件就会被抛弃：
   `View --> ViewGroup --> ~~ --> Activity`
-  dispatchTouchEvent方法用于事件的分发，Android中所有的事件都必须经过这个方法的分发，然后决定是自身消费当前事件还是继续往下分发给子控件处理。返回true表示不继续分发，事件没有被消费。返回false则继续往下分发，如果是ViewGroup则分发给onInterceptTouchEvent进行判断是否拦截该事件。

- onTouchEvent方法用于事件的处理，返回true表示消费处理当前事件，返回false则不处理，交给子控件进行继续分发。

- onInterceptTouchEvent是ViewGroup中才有的方法，View中没有，它的作用是负责事件的拦截，返回true的时候表示拦截当前事件，不继续往下分发，交给自身的onTouchEvent进行处理。返回false则不拦截，继续往下传。这是ViewGroup特有的方法，因为ViewGroup中可能还有子View，而在Android中View中是不能再包含子View的
- 上层View既可以直接拦截该事件，自己处理，也可以先询问(分发给)子View，如果子View需要就交给子View处理，如果子View不需要还能继续交给上层View处理。既保证了事件的有序性，又非常的灵活。
- 事件由父View传递给子View，ViewGroup可以通过onInterceptTouchEvent()方法对事件拦截，停止其向子view传递

- 如果View没有对ACTION_DOWN进行消费，之后的其他事件不会传递过来，也就是说ACTION_DOWN必须返回true，之后的事件才会传递进来

#### 2. ACTION_CANCEL什么时候触发

> 1.如果在父View中拦截ACTION_UP或ACTION_MOVE，在第一次父视图拦截消息的瞬间，父视图指定子视图不接受后续消息了，同时子视图会收到ACTION_CANCEL事件。
>
> 2.如果触摸某个控件，但是又不是在这个控件的区域上抬起（移动到别的地方了），就会出现action_cancel。

#### 3. 事件传递的层级

DecorView -> Activity -> PhoneWindow -> DecorView ->ViewGroup ->View

> 当屏幕被触摸input系统事件从Native层分发Framework层的**InputEventReceiver.dispachInputEvent()**调用了
>
> ViewRootImpl.WindowInputEventReceiver.dispachInputEvent()->ViewRootImpl中的
>
> DecorView.dispachInputEvent()->Activity.dispachInputEvent()->window.superDispatchTouchEvent()-
>
> \>DecorView.superDispatchTouchEvent()->Viewgroup.superDispatchTouchEvent()

#### 4. 在 ViewGroup **中的** onTouchEvent中消费 ACTION_DOWN 事件，ACTION_UP事件是怎么传递

一个事件序列只能被一个View拦截且消耗。因为一旦一个元素拦截了此事件，那么同一个事件序列内的所有事件都会直接交给它处理（即不会再调用这个View的拦截方法去询问它是否要拦截了，而是把剩余的ACTION_MOVE、 ACTION_DOWN等事件直接交给它来处理）。

> 假如一个view，在down事件来的时候 他的onTouchEvent返回false， 那么这个down事件 所属的事件序列 就是他后续的move 和up 都不会给他处理了，全部都给他的父view处理。

#### 5. 如果view 不消耗move或者up事件 会有什么结果？

那这个事件所属的事件序列就消失了，父view也不会处理的，最终都给activity 去处理了。



#### 5. Activity的分发方法中调用了onUserInteraction()的用处

这个方法在Activity接收到down的时候会被调用，本身是个空方法，需要开发者自己去重写。 通过官方的注释可以知道，这个方法会在我们以任意的方式**开始**与Activity进行交互的时候被调用。比较常见的场景就是屏保：当我们一段时间没有操作会显示一张图片，当我们开始与Activity交互的时候可在这个方法中取消屏保；另外还有没有操作自动隐藏工具栏，可以在这个方法中让工具栏重新显示。



#### 6. setOnTouchListener中onTouch的返回值表示什么意思？

onTouch方法返回true表示事件被消耗掉了，不会继续传递了,此时获取不到到OnClick和onLongClick事件；onTouch方法返回false表示事件没有被消耗，可以继续传递，此时，可以获取到OnClick和onLongClick事件；
 同理 onTouchEvent 和 setOnLongClickListener 方法中的返回值表示的意义一样；





#### 7. setOnLongClickListener的onLongClick的返回值表示什么？

返回false，长按的话会同时执行onLongClick和onClick；如果setOnLongClickListener返回true，表示事件被消耗，不会继续传递，只执行longClick；



#### 8. enable是否影响view的onTouchEvent返回值？

不影响，只要clickable和longClickable有一个为真，那么onTouchEvent就返回true。