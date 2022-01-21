---
title: Kotlin-委托
date: 2022-01-21 22:01:41
tags:
- Android
- Kotlin
---


# 前言

项目地址https://github.com/laibinzhi/KotlinDelegation

# 类委托

### 首先从类委托开始

```
interface IWork {
    fun work()
}

class Teacher : IWork {
    override fun work() {
        println("I am a teacher")
    }
}

class Police : IWork {
    override fun work() {
        println("I am a Police")
    }
}

class Tony(work: IWork) : IWork by work

fun main() {
    Tony(Teacher()).work()
    Tony(Police()).work()
}

```

```
打印:
I am a teacher
I am a Police
```

以上的代码当中，我们定义了一个 IWork 接口，它的 work() 方法用于表示该工作，Teacher 和 Police 都实现了这个接口。接着，我们的 Tony 也实现了这个接口，同时通过 by 这个关键字，将接口的实现委托给了它的参数 work。这种委托模式在我们的实际编程中十分常见，Tony 相当于一个壳，它虽然实现了 IWork 这个接口，但并不关心它怎么实现。具体是用 Teacher 还是 Police，传不同的委托对象进去，它就会有不同的行为。另外，以上委托类的写法，等价于以下 Java 代码，我们可以再进一步来看下：
<!--more-->


```
class Tony implements IWork {
    IWork work;
    public Tony(IWork work) { this.work = work; }
    //  手动重写接口，将 work 委托给 work.work()
    @Override//            ↓
    public void work() { work.work(); }
}
```

以上代码显示，work() 将执行流程委托给了传入的 work 对象。所以说，**Kotlin 的委托类提供了语法层面的委托模式。通过这个 by 关键字，就可以自动将接口里的方法委托给一个对象**，从而可以帮我们省略很多接口方法适配的模板代码。



另外有个问题，如果Tony这个类自己也实现IWork接口，那执行结果会是怎样？

```
class Tony(work: IWork) : IWork by work{
    override fun work() {
        println("I am a Tony")
    }
}
```

```
打印:
I am a Tony
I am a Tony
```

也就是说自己也提供接口的实现，会优先使用自己的实现。

### 委托的原理

**by关键字后面的对象实际上会被存储在类的内部，编译器则会父接口中的所有方法实现出来，并且将实现转移给委托对象去执行。**

# 属性委托

### 自定义属性委托

#### 1.要实现自定义属性委托，必须要遵循kotlin的规则。

```
class MyDelegate {
    operator fun setValue(thisRef: Any?, property: KProperty<*>, value: String) {
        println("setValue $thisRef,新的值是=$value")
    }

    operator fun getValue(thisRef: Any?, property: KProperty<*>): String {
        println("getValue $thisRef,你委托的属性名是= ${property.name}")
        return "world"
    }
}

class PropertyDelegationTest02 {
    var str: String by MyDelegate()
}

fun main() {
    val propertyDelegationTest02 = PropertyDelegationTest02()
    propertyDelegationTest02.str = "hello"
    println(propertyDelegationTest02.str)
}
```

```
打印:
setValue property_delegation.PropertyDelegationTest02@26a1ab54,新的值是=hello
getValue property_delegation.PropertyDelegationTest02@26a1ab54,你委托的属性名是= str
world
```

- 对于 var 修饰的属性，我们必须要有 getValue、setValue 这两个方法，同时，这两个方法必须有 operator 关键字修饰。对于val 修饰的属性，只需要有getValue方法即可
- 我们的 str 属性是处于 PropertyDelegationTest02 这个类当中的，因此 getValue、setValue 这两个方法中的 thisRef 的类型，必须要是 PropertyDelegationTest02，或者是 PropertyDelegationTest02 的父类。也就是说，我们将 thisRef 的类型改为 Any 也是可以的。一般来说，这三处的类型是一致的，当我们不确定委托属性会处于哪个类的时候，就可以将 thisRef 的类型定义为“Any?”。
- 由于我们的 str 属性是 String 类型的，为了实现对它的委托，getValue 的返回值类型，以及 setValue 的参数类型，都必须是 String 类型或者是它的父类。大部分情况下，这三处的类型都应该是一致的。

#### 2.借助 Kotlin 提供的 ReadWriteProperty、ReadOnlyProperty 实现自定义属性委托

```
public fun interface ReadOnlyProperty<in T, out V> {
    public operator fun getValue(thisRef: T, property: KProperty<*>): V
}

public interface ReadWriteProperty<in T, V> : ReadOnlyProperty<T, V> {
    public override operator fun getValue(thisRef: T, property: KProperty<*>): V

    public operator fun setValue(thisRef: T, property: KProperty<*>, value: V)
}
```

如果我们需要为 val 属性定义委托，我们就去实现 ReadOnlyProperty 这个接口；如果我们需要为 var 属性定义委托，我们就去实现 ReadWriteProperty 这个接口。这样做的好处是，通过实现接口的方式，AS 可以帮我们自动生成 override 的 getValue、setValue 方法。

以前面的代码为例，我们的 MyDelegateV2，也可以通过实现 ReadWriteProperty 接口来编写：

```
class MyDelegateV2 : ReadWriteProperty<PropertyDelegationTest02, String> {
    override fun getValue(thisRef: PropertyDelegationTest02, property: KProperty<*>): String {
        println("getValue $thisRef,你委托的属性名是= ${property.name}")
        return "world2"
    }

    override fun setValue(thisRef: PropertyDelegationTest02, property: KProperty<*>, value: String) {
        println("setValue $thisRef,新的值是=$value")
    }
}
```

```
打印:
setValue property_delegation.PropertyDelegationTest02@2ef1e4fa,新的值是=hello
getValue property_delegation.PropertyDelegationTest02@2ef1e4fa,你委托的属性名是= str
world2
```



### 延迟属性(懒加载属性)

懒加载，顾名思义，就是对于一些需要消耗计算机资源的操作，我们希望它在被访问的时候才去触发，从而避免不必要的资源开销。其实，这也是软件设计里十分常见的模式，我们来看一个例子：

```
val lazyValue: Int by lazy {
    println("world")
    10
}

fun main() {
    println(“hello”)
    println(lazyValue)
    println(lazyValue)
}
```

```
打印:
hello
world
10
10
```



通过“by lazy{}”，我们就可以实现属性的懒加载了。这样，通过上面的执行结果我们会发现：main() 函数的第一行代码，由于没有用到 lazyValue，所以不会去加载，第二句调用了lazyValue，才会去加载，第三句代码，之前已经获取了lazyValue的值，所以不会重新获取，直接返回。

换句话说：**属性只有第一次被访问的时候才会去计算，之后则会将之前的计算结果缓存起来供后续使用**

#### 延迟属性原理

lazy函数其实是一个高阶函数

```
public actual fun <T> lazy(initializer: () -> T): Lazy<T> = SynchronizedLazyImpl(initializer)

public actual fun <T> lazy(mode: LazyThreadSafetyMode, initializer: () -> T): Lazy<T> =
    when (mode) {
        LazyThreadSafetyMode.SYNCHRONIZED -> SynchronizedLazyImpl(initializer)
        LazyThreadSafetyMode.PUBLICATION -> SafePublicationLazyImpl(initializer)
        LazyThreadSafetyMode.NONE -> UnsafeLazyImpl(initializer)
    }
```

我们现在以SynchronizedLazyImpl为例子：

```
private class SynchronizedLazyImpl<out T>(initializer: () -> T, lock: Any? = null) : Lazy<T>, Serializable {
    private var initializer: (() -> T)? = initializer
    @Volatile private var _value: Any? = UNINITIALIZED_VALUE
    // final field is required to enable safe publication of constructed instance
    private val lock = lock ?: this

    override val value: T
        get() {
            val _v1 = _value
            //步骤1.如果_v1还没初始化，就会执行下面synchronized的代码块。
            //步骤4.如果是第二次获取这个值，判断UNINITIALIZED_VALUE已经被赋值了，
            if (_v1 !== UNINITIALIZED_VALUE) {
                @Suppress("UNCHECKED_CAST")
                return _v1 as T
            }

            return synchronized(lock) {
                //步骤2.如果_v2还没初始化，就会执行下面else的代码块。
                val _v2 = _value
                if (_v2 !== UNINITIALIZED_VALUE) {
                    @Suppress("UNCHECKED_CAST") (_v2 as T)
                } else {
                    val typedValue = initializer!!()
                    _value = typedValue
                    initializer = null
                    typedValue
                    //步骤3.初始化完成，返回初始化的值，同时更改UNINITIALIZED_VALUE的值
                }
            }
        }

    override fun isInitialized(): Boolean = _value !== UNINITIALIZED_VALUE

    override fun toString(): String = if (isInitialized()) value.toString() else "Lazy value not initialized yet."

    private fun writeReplace(): Any = InitializedLazyImpl(value)
}
```

可以看到，lazy() 函数可以接收一个 LazyThreadSafetyMode 类型的参数，如果我们不传这个参数，它就会直接使用 SynchronizedLazyImpl 的方式。

- SYNCHRONIZED：默认情况下，延迟属性的计算是同步的：值只会在一个线程中得到计算，所有线程都会使用相同的的一个结果。（多线程同步，多线程安全）
- PUBLICATION：如果不需要初始化委托的同步，这样多个线程可以同时执行。（多线程不安全）
- NONE：如果确定初始化操作只会在一个线程中执行，这样会减少线程安全方面的开销。（多线程不安全）

### 非空属性

适用于无法在初始化阶段就确定属性值的场合，因为Kotlin要求对于类里面的每一个属性必须赋予初值，这个可以直接赋一个具体值，也可以通过init代码块来进行赋初值，但终归有一个地方要求赋初值，但是某些情况下没有办法在初始化的时候去确定初始值是什么，这个情况下随便赋一个没有意义的值，（空字符串是没有意义的，相信很多人这么做）。那现在我们可以使Delegates.notNull委托去实现。

我们翻看一下Delegates.notNull的源码

```
public object Delegates {
    public fun <T : Any> notNull(): ReadWriteProperty<Any?, T> = NotNullVar()

    private class NotNullVar<T : Any>() : ReadWriteProperty<Any?, T> {
         private var value: T? = null

        public override fun getValue(thisRef: Any?, property: KProperty<*>): T {
        return value ?: throw IllegalStateException("Property ${property.name} should be          initialized before get.")
    }

      public override fun setValue(thisRef: Any?, property: KProperty<*>, value: T) {
        this.value = value
      }
    }
}

```

从代码上来看，如果在没有为这个属性赋值的情况下就去调用这个属性，就会抛出一个异常。例：

```
/**
 * 非空属性
 */
class NotNullPropertyDelegation {
    val userName: String by Delegates.notNull<String>()
}

fun main() {
    val notNullPropertyDelegation = NotNullPropertyDelegation()
    println(notNullPropertyDelegation.userName)
}

```

```
Exception in thread "main" java.lang.IllegalStateException: Property userName should be initialized before get.
	at kotlin.properties.NotNullVar.getValue(Delegates.kt:62)
	at property_delegation.NotNullPropertyDelegation.getUserName(NotNullPropertyDelegation.kt:6)
	at property_delegation.NotNullPropertyDelegationKt.main(NotNullPropertyDelegation.kt:11)
	at property_delegation.NotNullPropertyDelegationKt.main(NotNullPropertyDelegation.kt)
```

如果在调用之前，赋一个值给userName就不会抛异常了！！！

### 可观察属性

#### Delegates.observable

Delegates.observable 返回读取/写入属性的属性委托，该属性在更改时调用指定的回调函数。

```
    public inline fun <T> observable(initialValue: T, crossinline onChange: (property: KProperty<*>, oldValue: T, newValue: T) -> Unit):
            ReadWriteProperty<Any?, T> =
        object : ObservableProperty<T>(initialValue) {
            override fun afterChange(property: KProperty<*>, oldValue: T, newValue: T) = onChange(property, oldValue, newValue)
        }
```

接收两个参数，参数initialValue表示属性的初始值，onChange表示属性更改后调用的回调。 调用此回调时，该属性的值已更改。onChange有三个参数，被赋值属性本身，旧的值，和新的值，接下来，我们看一下用法。例如：

```
class Person {
    var age: Int by Delegates.observable(10) { property, oldValue, newValue ->
        println("onChange property.name=" + property.name + "   oldValue=" + oldValue + "   newValue=" + newValue)
    }
}

fun main() {
    val person = Person()
    println(person.age)
    person.age = 20
    println(person.age)
}
```

```
打印:
10
property=age   oldValue=10   newValue=20
20

```

#### Delegates.vetoable

另外，如果你想拦截改属性的话，可以使用vetoable函数。返回读取/写入属性的属性委托，该属性在更改时调用指定的回调函数，允许回调否决修改。

```
   public inline fun <T> vetoable(initialValue: T, crossinline onChange: (property: KProperty<*>, oldValue: T, newValue: T) -> Boolean):
            ReadWriteProperty<Any?, T> =
        object : ObservableProperty<T>(initialValue) {
            override fun beforeChange(property: KProperty<*>, oldValue: T, newValue: T): Boolean = onChange(property, oldValue, newValue)
        }
```

同样，接收两个参数，initialValue表示熟悉的初始值，onChange，在尝试更改属性值之前调用的回调。 调用此回调时，该属性的值尚未更改。 如果回调返回true ，则将属性的值设置为新值，如果回调返回false ，则丢弃新值，并且属性保持其旧值。调用时机和Delegates.observable相反，接下来，我们看一下用法，例：

```
class Person {
    var level: Int by Delegates.vetoable(10) { property, oldValue, newValue ->
        println("onChange property.name=" + property.name + "   oldValue=" + oldValue + "   newValue=" + newValue)
        newValue >= oldValue
    }
}

fun main() {
    println("-----------------------------------------")
    println(person.level)
    person.level = 20
    println("person.level="+person.level)
    person.level = 5
    println("person.level="+person.level)
}
```

```
打印:
-----------------------------------------
10
onChange property.name=level   oldValue=10   newValue=20
person.level=20
onChange property.name=level   oldValue=20   newValue=5
person.level=20

```

从结果可以看出，第一次获取level的值可以直接读取初始值10出来，然后第一次负责20，我们也可以从onChange得到值更改出来，并且新的值>=旧的值，所以允许修改，所以我们看到打印新的等级是20。然后我们尝试改一个新值比旧值小的数，发现level并没有修改成功。

### map属性

将属性储存在map中，一种常见的应用场景就是将属性值存储到map中，用于json解析或者是一些动态行为，在这种情况下，您可以使用map实例本身作为委托属性的委托。

```
class User(map: Map<String, Any?>) {
    val name: String by map
    val age: Int by map
}

fun main() {
    val user = User(mapOf("name" to "Wang", "age" to 25))
    println(user.name)  // Prints "Wang"
    println(user.age)  // Prints 25
}
```

注意：map中key的名字要与类中属性的名字保持一致，不然会报错

```
Exception in thread "main" java.util.NoSuchElementException: Key name is missing in the map.
	at kotlin.collections.MapsKt__MapWithDefaultKt.getOrImplicitDefaultNullable(MapWithDefault.kt:24)
	at property_delegation.User.getName(MapPropertyDelegation.kt:4)
	at property_delegation.MapPropertyDelegationKt.main(MapPropertyDelegation.kt:10)
	at property_delegation.MapPropertyDelegationKt.main(MapPropertyDelegation.kt)

```

### 提供委托（provideDelegate）

我们看一下StringDelegate这个例子，是最基础的属性委托。

```
class StringDelegate(private var s: String = "Hello"): ReadWriteProperty<Owner, String> {
    override operator fun getValue(thisRef: Owner, property: KProperty<*>): String {
        return s
    }
    override operator fun setValue(thisRef: Owner, property: KProperty<*>, value: String) {
        s = value
    }
}
```

我们希望 StringDelegate(s: String) 传入的初始值 s，可以根据委托属性的名字的变化而变化。我们应该怎么做？

实际上，要想在属性委托之前再做一些额外的判断工作，我们可以使用 provideDelegate 来实现。

```
class StudentDelegator {
    operator fun provideDelegate(thisRef: Student, prop: KProperty<*>): ReadWriteProperty<Student, String> {
        return if (prop.name.contains("userName")) {
            StringDelegate("userName")
        } else {
            StringDelegate("country")
        }
    }
}

class Student {
    var userName: String by StudentDelegator()
    var country: String by StudentDelegator()
}

fun main() {
    val student = Student()
    println(student.userName)
    println(student.country)
}
```

```
打印:
userName
country
```

为了在委托属性的同时进行一些额外的逻辑判断，我们使用创建了一个新的 StudentDelegator，通过它的成员方法 provideDelegate 嵌套了一层，在这个方法当中，我们进行了一些逻辑判断，然后再把属性委托给 StringDelegate。

如此一来，通过 provideDelegate 这样的方式，我们不仅可以嵌套 Delegator，还可以根据不同的逻辑派发不同的 Delegator。

### 属性委托总结

#### ReadOnlyProperty和ReadWriteProperty



```
可用于实现只读属性的属性委托的基本接口。
这只是为了方便； 只要您的属性委托具有具有相同签名的方法，您就不必扩展此接口。
参数T:拥有委托属性的对象类型
参数V:属性值的类型
public fun interface ReadOnlyProperty<in T, out V> {
    /**
     * 返回给定对象的属性值。
     * @param thisRef 为其请求值的对象
     * @param property 属性的元数据
     * @return 属性值
     */
    public operator fun getValue(thisRef: T, property: KProperty<*>): V
}

```

```
可用于实现读写属性的属性委托的基本接口。
这只是为了方便； 只要您的属性委托具有具有相同签名的方法，您就不必扩展此接口。
参数T:拥有委托属性的对象类型
参数V:属性值的类型
public interface ReadWriteProperty<in T, V> : ReadOnlyProperty<T, V> {
     /**
     * 返回给定对象的属性值。
     * @param thisRef 为其请求值的对象
     * @param property 属性的元数据
     * @return 属性值
     */
    public override operator fun getValue(thisRef: T, property: KProperty<*>): V

    /**
     * 设置给定对象的属性值。
     * @param thisRef 为其请求值的对象
     * @param property 属性的元数据
     * @param value 要设置的值
     */
    public operator fun setValue(thisRef: T, property: KProperty<*>, value: V)
}
```



#### 对于属性委托的要求

对于只读属性来说（val修饰的属性），委托需要提供一个名为getValue的方法，该方法接收如下参数：

- thisRef：需要是属性拥有者相同的类型或者是其父类型（对于拓展属性来说，这个类型指的是被拓展的那个类型）。
- property：需要的是KProperty<*>类型或者是其父类型。

对于getValue()方法需要返回与属性相同的类型或者是子类型



对于可变属性来说（var修饰的属性），委托需要提供一个名为setValue的方法，该方法要接受以下参数：

- thisRef：需要是属性拥有者相同的类型或者是其父类型（对于拓展属性来说，这个类型指的是被拓展的那个类型）。
- property：需要的是KProperty<*>类型或者是其父类型。
- new value：需要与属性的类型相同或者其父类型

getValue和setValue既可以作为委托类的成员方法实现，也可以成为其拓展方法来实现

这两个方法都要有**operator**关键字，对于委托类来说，他可以实现ReadWriteProperty、ReadOnlyProperty的接口，这两个接口包含了响应的getValue和setValue方法。

#### 委托转换规则

对于每个委托属性来说，Kotlin编译器在底层会生成一个辅助的属性，然后将对原有属性的访问委托给这个辅助属性。



# 委托的实际运用

### 1.属性可见性封装

假设你有一个ArrayList的实例，可以恢复其最后删除的项目，基本上，你需要的就是和ArrayList一样的功能，同时还需要一个最后一个被移除元素的引用。一种方法就是集成自ArrayList，由于新的类是集成具体的ArrayList，而不是实现了MutableList接口，因此新的类的实现方式和ArrayList存在高度的耦合。那如果是覆盖remove方法，是不是一个好的方法？通过保留已删除item的引用，并委派MutableList的大部分空的实现给其他的对象。Kotlin的类委托就可以很好的实现。通过委托大多数工作给一个内部的ArrayList实例去实现，并且可以自定义它自己的行为。

```
class ListWithTrash<T>(private val innerList: MutableList<T> = ArrayList()) : MutableList<T> by innerList {
    var deletedItem: T? = null
    override fun remove(element: T): Boolean {
        deletedItem = element
        return innerList.remove(element)
    }

    fun recover(): T? {
        return deletedItem
    }
}

fun main() {
    val listWithTrash = ListWithTrash(arrayListOf(1, 2, 3))
    listWithTrash.remove(2)
    println("被删除的元素是=" + listWithTrash.recover())
}
```

上面by关键字告诉Kotlin委托功能将会被一个内部名为innerList的ArrayList去实现代理，ListWithTrash仍然支持所有方法功能。通过提供桥接方法在可变MutableList界面中到内部ArrayList对象。还可以定义自己的行为。反编译看他的内部，其实还是会实现ArrayList的所有方法。

```
package property_delegation;

import java.util.List;
import kotlin.Metadata;
import kotlin.collections.CollectionsKt;

@Metadata(
   mv = {1, 5, 1},
   k = 2,
   d1 = {"\u0000\b\n\u0000\n\u0002\u0010\u0002\n\u0000\u001a\u0006\u0010\u0000\u001a\u00020\u0001¨\u0006\u0002"},
   d2 = {"main", "", "KotlinDelegation.main"}
)
public final class Example01Kt {
   public static final void main() {
      ListWithTrash listWithTrash = new ListWithTrash((List)CollectionsKt.arrayListOf(new Integer[]{1, 2, 3}));
      listWithTrash.remove(2);
      String var1 = "被删除的元素是=" + (Integer)listWithTrash.recover();
      boolean var2 = false;
      System.out.println(var1);
   }

   // $FF: synthetic method
   public static void main(String[] var0) {
      main();
   }
}
// ListWithTrash.java
package property_delegation;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Iterator;
import java.util.List;
import java.util.ListIterator;
import kotlin.Metadata;
import kotlin.jvm.internal.CollectionToArray;
import kotlin.jvm.internal.DefaultConstructorMarker;
import kotlin.jvm.internal.Intrinsics;
import kotlin.jvm.internal.markers.KMutableList;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

@Metadata(
   mv = {1, 5, 1},
   k = 1,
   d1 = {"\u0000>\n\u0002\u0018\u0002\n\u0000\n\u0002\u0010!\n\u0002\b\t\n\u0002\u0010\b\n\u0002\b\u0003\n\u0002\u0010\u000b\n\u0002\b\u0002\n\u0002\u0010\u0002\n\u0002\b\u0004\n\u0002\u0010\u001e\n\u0002\b\t\n\u0002\u0010)\n\u0002\b\u0002\n\u0002\u0010+\n\u0002\b\u000b\u0018\u0000*\u0004\b\u0000\u0010\u00012\b\u0012\u0004\u0012\u0002H\u00010\u0002B\u0015\u0012\u000e\b\u0002\u0010\u0003\u001a\b\u0012\u0004\u0012\u00028\u00000\u0002¢\u0006\u0002\u0010\u0004J\u0016\u0010\u000f\u001a\u00020\u00102\u0006\u0010\u0011\u001a\u00028\u0000H\u0096\u0001¢\u0006\u0002\u0010\u0012J\u001e\u0010\u000f\u001a\u00020\u00132\u0006\u0010\u0014\u001a\u00020\f2\u0006\u0010\u0011\u001a\u00028\u0000H\u0096\u0001¢\u0006\u0002\u0010\u0015J\u001f\u0010\u0016\u001a\u00020\u00102\u0006\u0010\u0014\u001a\u00020\f2\f\u0010\u0017\u001a\b\u0012\u0004\u0012\u00028\u00000\u0018H\u0096\u0001J\u0017\u0010\u0016\u001a\u00020\u00102\f\u0010\u0017\u001a\b\u0012\u0004\u0012\u00028\u00000\u0018H\u0096\u0001J\t\u0010\u0019\u001a\u00020\u0013H\u0096\u0001J\u0016\u0010\u001a\u001a\u00020\u00102\u0006\u0010\u0011\u001a\u00028\u0000H\u0096\u0003¢\u0006\u0002\u0010\u0012J\u0017\u0010\u001b\u001a\u00020\u00102\f\u0010\u0017\u001a\b\u0012\u0004\u0012\u00028\u00000\u0018H\u0096\u0001J\u0016\u0010\u001c\u001a\u00028\u00002\u0006\u0010\u0014\u001a\u00020\fH\u0096\u0003¢\u0006\u0002\u0010\u001dJ\u0016\u0010\u001e\u001a\u00020\f2\u0006\u0010\u0011\u001a\u00028\u0000H\u0096\u0001¢\u0006\u0002\u0010\u001fJ\t\u0010 \u001a\u00020\u0010H\u0096\u0001J\u000f\u0010!\u001a\b\u0012\u0004\u0012\u00028\u00000\"H\u0096\u0003J\u0016\u0010#\u001a\u00020\f2\u0006\u0010\u0011\u001a\u00028\u0000H\u0096\u0001¢\u0006\u0002\u0010\u001fJ\u000f\u0010$\u001a\b\u0012\u0004\u0012\u00028\u00000%H\u0096\u0001J\u0017\u0010$\u001a\b\u0012\u0004\u0012\u00028\u00000%2\u0006\u0010\u0014\u001a\u00020\fH\u0096\u0001J\r\u0010&\u001a\u0004\u0018\u00018\u0000¢\u0006\u0002\u0010\u0007J\u0015\u0010'\u001a\u00020\u00102\u0006\u0010\u0011\u001a\u00028\u0000H\u0016¢\u0006\u0002\u0010\u0012J\u0017\u0010(\u001a\u00020\u00102\f\u0010\u0017\u001a\b\u0012\u0004\u0012\u00028\u00000\u0018H\u0096\u0001J\u0016\u0010)\u001a\u00028\u00002\u0006\u0010\u0014\u001a\u00020\fH\u0096\u0001¢\u0006\u0002\u0010\u001dJ\u0017\u0010*\u001a\u00020\u00102\f\u0010\u0017\u001a\b\u0012\u0004\u0012\u00028\u00000\u0018H\u0096\u0001J\u001e\u0010+\u001a\u00028\u00002\u0006\u0010\u0014\u001a\u00020\f2\u0006\u0010\u0011\u001a\u00028\u0000H\u0096\u0003¢\u0006\u0002\u0010,J\u001f\u0010-\u001a\b\u0012\u0004\u0012\u00028\u00000\u00022\u0006\u0010.\u001a\u00020\f2\u0006\u0010/\u001a\u00020\fH\u0096\u0001R\u001e\u0010\u0005\u001a\u0004\u0018\u00018\u0000X\u0086\u000e¢\u0006\u0010\n\u0002\u0010\n\u001a\u0004\b\u0006\u0010\u0007\"\u0004\b\b\u0010\tR\u0014\u0010\u0003\u001a\b\u0012\u0004\u0012\u00028\u00000\u0002X\u0082\u0004¢\u0006\u0002\n\u0000R\u0012\u0010\u000b\u001a\u00020\fX\u0096\u0005¢\u0006\u0006\u001a\u0004\b\r\u0010\u000e¨\u00060"},
   d2 = {"Lproperty_delegation/ListWithTrash;", "T", "", "innerList", "(Ljava/util/List;)V", "deletedItem", "getDeletedItem", "()Ljava/lang/Object;", "setDeletedItem", "(Ljava/lang/Object;)V", "Ljava/lang/Object;", "size", "", "getSize", "()I", "add", "", "element", "(Ljava/lang/Object;)Z", "", "index", "(ILjava/lang/Object;)V", "addAll", "elements", "", "clear", "contains", "containsAll", "get", "(I)Ljava/lang/Object;", "indexOf", "(Ljava/lang/Object;)I", "isEmpty", "iterator", "", "lastIndexOf", "listIterator", "", "recover", "remove", "removeAll", "removeAt", "retainAll", "set", "(ILjava/lang/Object;)Ljava/lang/Object;", "subList", "fromIndex", "toIndex", "KotlinDelegation.main"}
)
public final class ListWithTrash implements List, KMutableList {
   @Nullable
   private Object deletedItem;
   private final List innerList;

   @Nullable
   public final Object getDeletedItem() {
      return this.deletedItem;
   }

   public final void setDeletedItem(@Nullable Object var1) {
      this.deletedItem = var1;
   }

   public boolean remove(Object element) {
      this.deletedItem = element;
      return this.innerList.remove(element);
   }

   @Nullable
   public final Object recover() {
      return this.deletedItem;
   }

   public ListWithTrash(@NotNull List innerList) {
      Intrinsics.checkNotNullParameter(innerList, "innerList");
      super();
      this.innerList = innerList;
   }

   // $FF: synthetic method
   public ListWithTrash(List var1, int var2, DefaultConstructorMarker var3) {
      if ((var2 & 1) != 0) {
         var1 = (List)(new ArrayList());
      }

      this(var1);
   }

   public ListWithTrash() {
      this((List)null, 1, (DefaultConstructorMarker)null);
   }

   public int getSize() {
      return this.innerList.size();
   }

   // $FF: bridge method
   public final int size() {
      return this.getSize();
   }

   public boolean add(Object element) {
      return this.innerList.add(element);
   }

   public void add(int index, Object element) {
      this.innerList.add(index, element);
   }

   public boolean addAll(int index, @NotNull Collection elements) {
      Intrinsics.checkNotNullParameter(elements, "elements");
      return this.innerList.addAll(index, elements);
   }

   public boolean addAll(@NotNull Collection elements) {
      Intrinsics.checkNotNullParameter(elements, "elements");
      return this.innerList.addAll(elements);
   }

   public void clear() {
      this.innerList.clear();
   }

   public boolean contains(Object element) {
      return this.innerList.contains(element);
   }

   public boolean containsAll(@NotNull Collection elements) {
      Intrinsics.checkNotNullParameter(elements, "elements");
      return this.innerList.containsAll(elements);
   }

   public Object get(int index) {
      return this.innerList.get(index);
   }

   public int indexOf(Object element) {
      return this.innerList.indexOf(element);
   }

   public boolean isEmpty() {
      return this.innerList.isEmpty();
   }

   @NotNull
   public Iterator iterator() {
      return this.innerList.iterator();
   }

   public int lastIndexOf(Object element) {
      return this.innerList.lastIndexOf(element);
   }

   @NotNull
   public ListIterator listIterator() {
      return this.innerList.listIterator();
   }

   @NotNull
   public ListIterator listIterator(int index) {
      return this.innerList.listIterator(index);
   }

   public boolean removeAll(@NotNull Collection elements) {
      Intrinsics.checkNotNullParameter(elements, "elements");
      return this.innerList.removeAll(elements);
   }

   public Object removeAt(int index) {
      return this.innerList.remove(index);
   }

   // $FF: bridge method
   public final Object remove(int var1) {
      return this.removeAt(var1);
   }

   public boolean retainAll(@NotNull Collection elements) {
      Intrinsics.checkNotNullParameter(elements, "elements");
      return this.innerList.retainAll(elements);
   }

   public Object set(int index, Object element) {
      return this.innerList.set(index, element);
   }

   @NotNull
   public List subList(int fromIndex, int toIndex) {
      return this.innerList.subList(fromIndex, toIndex);
   }

   public Object[] toArray() {
      return CollectionToArray.toArray(this);
   }

   public Object[] toArray(Object[] var1) {
      return CollectionToArray.toArray(this, var1);
   }
}

```

### 2.数据与 View 的绑定

在 Android 当中，如果我们要对“数据”与“View”进行绑定，我们可以用 DataBinding，不过 DataBinding 太重了，也会影响编译速度。其实，除了 DataBinding 以外，我们还可以借助 Kotlin 的自定义委托属性来实现类似的功能。这种方式不一定完美，但也是一个有趣的思路。这里我们以 TextView 为例：

```

operator fun TextView.provideDelegate(value: Any?, property: KProperty<*>) = object : ReadWriteProperty<Any?, String?> {
    override fun getValue(thisRef: Any?, property: KProperty<*>): String? = text
    override fun setValue(thisRef: Any?, property: KProperty<*>, value: String?) {
        text = value
    }
}
```

以上的代码，我们为 TextView 定义了一个扩展函数 TextView.provideDelegate，而这个扩展函数的返回值类型是 ReadWriteProperty。通过这样的方式，我们的 TextView 就相当于支持了 String 属性的委托了。它的使用方式也很简单：

```

val textView = findViewById<textView>(R.id.textView)

// 通过委托的方式，将 message 委托给了 textView。这意味着，message 的 getter 和 setter 都将与 TextView 关联到一起。
var message: String? by textView

// 我们修改了 textView 的 text 属性，由于我们的 message 也委托给了 textView，因此这时候，println(message) 的结果也会变成“Hello”。
textView.text = "Hello"
println(message)

// 我们改为修改 message 的值，由于 message 的 setter 也委托给了 textView，因此这时候，println(textView.text) 的结果会跟着变成“World”。
message = "World"
println(textView.text)


结果：
Hello
World
```

# 总结

- 委托类，委托的是接口的方法，它在语法层面支持了“委托模式”。
- 委托属性，委托的是属性的 getter、setter。虽然它的核心理念很简单，但我们借助这个特性可以设计出非常复杂的代码。
- 另外，Kotlin 官方还提供了几种标准的属性委托，它们分别是：两个属性之间的直接委托、by lazy 懒加载委托、Delegates.observable 观察者委托，以及 by map 映射委托；
- 两个属性之间的直接委托，它是 Kotlin 1.4 提供的新特性，它在属性版本更新、可变性封装上，有着很大的用处；
- by lazy 懒加载委托，可以让我们灵活地使用懒加载，它一共有三种线程同步模式，默认情况下，它就是线程安全的；Android 当中的 viewModels() 这个扩展函数在它的内部实现的懒加载委托，从而实现了功能强大的 ViewModel；
- 除了标准委托以外，Kotlin 可以让我们开发者自定义委托。
- 自定义委托，我们需要遵循 Kotlin 提供的一套语法规范，只要符合这套语法规范，就没问题；在自定义委托的时候，如果我们有灵活的需求时，可以使用 provideDelegate 来动态调整委托逻辑。