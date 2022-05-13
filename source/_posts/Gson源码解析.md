---
title: Gson源码解析
date: 2022-05-09 10:23:43
tags:
  - Android
  - Java  
  - Gson
  - 序列化
  - 源码
---

# Gson源码解析

## 简介

Gson 是一个 Java 库，可用于将 Java 对象转换为其 JSON 表示形式。它还可用于将 JSON 字符串转换为等效的 Java 对象。

**地址**https://github.com/google/gson

```
dependencies {
  implementation 'com.google.code.gson:gson:2.9.0'
}
```

<!--more-->


## 简单使用

```java
public class Person {

    private String name;
    private Integer age;

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public Integer getAge() {
        return age;
    }

    public void setAge(Integer age) {
        this.age = age;
    }
}
```

```java
public class JsonTest {

    public static void main(String[] args){
        String json =
                "{" +
                "   \"name\": \"laibinzhi\"," +
                "   \"age\": 19" +
                "}";

        Gson gson = new Gson();
        
         //序列化
        String json2 = gson.toJson(person);
        System.out.println(json2);

        //反序列化
        Person person = gson.fromJson(json,Person.class);
        System.out.println(person.getName());
        System.out.println(person.getAge());

    }
}
```

## 源码分析

### 构造方法

#### 无参构造器

```java
 public Gson() {
    this(Excluder.DEFAULT, DEFAULT_FIELD_NAMING_STRATEGY,
        Collections.<Type, InstanceCreator<?>>emptyMap(), DEFAULT_SERIALIZE_NULLS,
        DEFAULT_COMPLEX_MAP_KEYS, DEFAULT_JSON_NON_EXECUTABLE, DEFAULT_ESCAPE_HTML,
        DEFAULT_PRETTY_PRINT, DEFAULT_LENIENT, DEFAULT_SPECIALIZE_FLOAT_VALUES,
        DEFAULT_USE_JDK_UNSAFE,
        LongSerializationPolicy.DEFAULT, DEFAULT_DATE_PATTERN, DateFormat.DEFAULT, DateFormat.DEFAULT,
        Collections.<TypeAdapterFactory>emptyList(), Collections.<TypeAdapterFactory>emptyList(),
        Collections.<TypeAdapterFactory>emptyList(), DEFAULT_OBJECT_TO_NUMBER_STRATEGY, DEFAULT_NUMBER_TO_NUMBER_STRATEGY);
  }
```



#### 有参构造器

```java
Gson(Excluder excluder, FieldNamingStrategy fieldNamingStrategy,
      Map<Type, InstanceCreator<?>> instanceCreators, boolean serializeNulls,
      boolean complexMapKeySerialization, boolean generateNonExecutableGson, boolean htmlSafe,
      boolean prettyPrinting, boolean lenient, boolean serializeSpecialFloatingPointValues,
      boolean useJdkUnsafe,
      LongSerializationPolicy longSerializationPolicy, String datePattern, int dateStyle,
      int timeStyle, List<TypeAdapterFactory> builderFactories,
      List<TypeAdapterFactory> builderHierarchyFactories,
      List<TypeAdapterFactory> factoriesToBeAdded,
      ToNumberStrategy objectToNumberStrategy, ToNumberStrategy numberToNumberStrategy) {
    //排除器，在序列化对象的时候会根据使用者设置的规则排除一些数据,
    //排除策略需要使用者自行实现 ExclusionStrategy 接口来制定
    this.excluder = excluder;
    //fieldNamingStrategy 负责命名规则的确定(比如 大驼峰命名、小驼峰命名、下划线命名 等)
    //选择不同的 fieldNamingStrategy 会在输出 json 字符串的时候把字段名称转成不同的命名形式
    this.fieldNamingStrategy = fieldNamingStrategy;
 
    this.constructorConstructor = new ConstructorConstructor(instanceCreators, useJdkUnsafe);
    ///serializeNulls 是一个 boolean 类型的对象，用以表示是否支持空对象的序列化
    this.serializeNulls = serializeNulls;
    this.complexMapKeySerialization = complexMapKeySerialization;
    //是否要生成不可执行的 json
    this.generateNonExecutableJson = generateNonExecutableGson;
    //是否对 html 进行编码，即对部分符号进行转义(=、<、> 等)
    this.htmlSafe = htmlSafe;
    //在输出的时候格式化 json
    this.prettyPrinting = prettyPrinting;
    ...

    //TypeAdapter 是一个接口，用于序列化和反序列化某种特定的类型
    //TypeAdapterFactory 是 TypeAdapter 的包装类
    List<TypeAdapterFactory> factories = new ArrayList<TypeAdapterFactory>();

    //处理 JsonElement 类型对象的 TypeAdapterFactory
    factories.add(TypeAdapters.JSON_ELEMENT_FACTORY);
    //处理 Object 类型对象的 TypeAdapterFactory
    factories.add(ObjectTypeAdapter.getFactory(objectToNumberStrategy));

    //excluder 是一个省略了类型的 TypeAdapterFactory,根据官方注释，excluder 需要先于所有使用者自定义的 TypeAdapterFactory 去执行
    factories.add(excluder);

    // 处理使用者自定义的 TypeAdapterFactory
    factories.addAll(factoriesToBeAdded);

    //处理基本类型的TypeAdapterFactory
    factories.add(TypeAdapters.STRING_FACTORY);
    factories.add(TypeAdapters.INTEGER_FACTORY);
    factories.add(TypeAdapters.BOOLEAN_FACTORY);
    factories.add(TypeAdapters.BYTE_FACTORY);
    factories.add(TypeAdapters.SHORT_FACTORY);
    TypeAdapter<Number> longAdapter = longAdapter(longSerializationPolicy);
    factories.add(TypeAdapters.newFactory(long.class, Long.class, longAdapter));
    factories.add(TypeAdapters.newFactory(double.class, Double.class,
            doubleAdapter(serializeSpecialFloatingPointValues)));
    factories.add(TypeAdapters.newFactory(float.class, Float.class,
            floatAdapter(serializeSpecialFloatingPointValues)));
    factories.add(NumberTypeAdapter.getFactory(numberToNumberStrategy));
    factories.add(TypeAdapters.ATOMIC_INTEGER_FACTORY);
    factories.add(TypeAdapters.ATOMIC_BOOLEAN_FACTORY);
    factories.add(TypeAdapters.newFactory(AtomicLong.class, atomicLongAdapter(longAdapter)));
    factories.add(TypeAdapters.newFactory(AtomicLongArray.class, atomicLongArrayAdapter(longAdapter)));
    factories.add(TypeAdapters.ATOMIC_INTEGER_ARRAY_FACTORY);
    factories.add(TypeAdapters.CHARACTER_FACTORY);
    factories.add(TypeAdapters.STRING_BUILDER_FACTORY);
    factories.add(TypeAdapters.STRING_BUFFER_FACTORY);
    factories.add(TypeAdapters.newFactory(BigDecimal.class, TypeAdapters.BIG_DECIMAL));
    factories.add(TypeAdapters.newFactory(BigInteger.class, TypeAdapters.BIG_INTEGER));
    // Add adapter for LazilyParsedNumber because user can obtain it from Gson and then try to serialize it again
    factories.add(TypeAdapters.newFactory(LazilyParsedNumber.class, TypeAdapters.LAZILY_PARSED_NUMBER));
    factories.add(TypeAdapters.URL_FACTORY);
    factories.add(TypeAdapters.URI_FACTORY);
    factories.add(TypeAdapters.UUID_FACTORY);
    factories.add(TypeAdapters.CURRENCY_FACTORY);
    factories.add(TypeAdapters.LOCALE_FACTORY);
    factories.add(TypeAdapters.INET_ADDRESS_FACTORY);
    factories.add(TypeAdapters.BIT_SET_FACTORY);
    factories.add(DateTypeAdapter.FACTORY);
    factories.add(TypeAdapters.CALENDAR_FACTORY);

    if (SqlTypesSupport.SUPPORTS_SQL_TYPES) {
      factories.add(SqlTypesSupport.TIME_FACTORY);
      factories.add(SqlTypesSupport.DATE_FACTORY);
      factories.add(SqlTypesSupport.TIMESTAMP_FACTORY);
    }

    factories.add(ArrayTypeAdapter.FACTORY);
    factories.add(TypeAdapters.CLASS_FACTORY);

    // type adapters for composite and user-defined types
    factories.add(new CollectionTypeAdapterFactory(constructorConstructor));
    factories.add(new MapTypeAdapterFactory(constructorConstructor, complexMapKeySerialization));
    this.jsonAdapterFactory = new JsonAdapterAnnotationTypeAdapterFactory(constructorConstructor);
    factories.add(jsonAdapterFactory);
    factories.add(TypeAdapters.ENUM_FACTORY);
    //反射分解对象的 TypeAdapterFactory，此处放到最后，因为ReflectiveTypeAdapterFactory能适配以上所有
    factories.add(new ReflectiveTypeAdapterFactory(
        constructorConstructor, fieldNamingStrategy, excluder, jsonAdapterFactory));

    this.factories = Collections.unmodifiableList(factories);
  }
```

### GsonBuilder

```java
Gson gson = new GsonBuilder()

    //设置版本号
    .setVersion(1)
    //设置忽略某种修饰词修饰的变量，此处忽略 protected 修饰的变量
    .excludeFieldsWithModifiers(Modifier.PROTECTED)
    //设置使用 Expose 注解，用于忽略某个字段，默认情况下是不使用 Expose 注解的
    .excludeFieldsWithoutExposeAnnotation()
    //设置不序列化内部类
    .disableInnerClassSerialization()
    //批量添加序列化时使用的排除策略，此方法为不定参方法
    .setExclusionStrategies(exclusionStrategy)
    //添加一个序列化时使用的排除策略
    .addSerializationExclusionStrategy(exclusionStrategy)
    //添加一个反序列化时使用的排除策略
    .addDeserializationExclusionStrategy(exclusionStrategy)

    //本质上以下三个方法均为设置 TypeAdapter
    .registerTypeAdapter(String.class, TypeAdapters.STRING)
    .registerTypeAdapterFactory(TypeAdapters.STRING_FACTORY)
    .registerTypeHierarchyAdapter(String.class, TypeAdapters.STRING)

    //设置 dateStyle、datePattern、timeStyle
    .setDateFormat("yyyy-MM-dd HH:mm:ss")
    .setDateFormat(DateFormat.DATE_FIELD)
    .setDateFormat(DateFormat.DATE_FIELD,DateFormat.AM_PM_FIELD)

    //以下两个方法本质上是一样的，均为设置 fieldNamingPolicy 属性
    .setFieldNamingPolicy(FieldNamingPolicy.IDENTITY)
    .setFieldNamingStrategy(FieldNamingPolicy.IDENTITY)

    //设置 complexMapKeySerialization = true
    .enableComplexMapKeySerialization()

    //设置 longSerializationPolicy = LongSerializationPolicy.STRING
    //即 long 类型的数据在序列化的时候会转成 String
    .setLongSerializationPolicy(LongSerializationPolicy.STRING)

    //设置 serializeNulls = true
    .serializeNulls()

    //设置 prettyPrinting = true
    .setPrettyPrinting()

    //设置 generateNonExecutableJson = true
    .generateNonExecutableJson()

    //设置 lenient = true
    .setLenient()

    //设置 escapeHtmlChars = false
    .disableHtmlEscaping()

    //设置 serializeSpecialFloatingPointValues = true
    .serializeSpecialFloatingPointValues()

    //创建解析器对象
    .create();
```



### TypeAdapter

TypeAdapter是Gson的核心，它的设计是一个**适配器模式**

因为**Json**数据接口和**Type**的接口两者是无法兼容，因此**TypeAdapter**就是来实现兼容，把**json**数据读到**Type**中，把**Type**中的数据写入到**Json**里。

![image](https://s2.loli.net/2022/05/09/x5VXkPGSZa8mjrl.png)



```java
public abstract class TypeAdapter<T> {
  //写入方法，主要的指挥 JsonWriter 进行业务处理
  public abstract void write(JsonWriter out, T value) throws IOException;
  //读取方法，主要是指挥 JsonReader 进行业务操作
  public abstract T read(JsonReader in) throws IOException;
}
```



![](https://s2.loli.net/2022/05/09/s4t6hlT37ZcanuX.png)



Gson会为每一种类型创建一个TypeAdapter，同样的，每一个Type都对应唯一一个TypeAdapter

而所有Type(类型)，在Gson中又可以分为基本类型和复合类型（非基本类型）

 

- 基本类型（Integer,String,Uri,Url,Calendar...）

- 复合类型（非基本类型）：即除了基本类型之外的类型




![](https://s2.loli.net/2022/05/09/DS4Cp3tF5aosmRj.png)



- 流程简图

  ![](https://s2.loli.net/2022/05/09/ylBpVfg79HGUrTK.png)



### TypeAdapterFactory

在 Gson 中封装了不同类型的读写的业务组装类是各个 TypeAdapter(适配器)

```java
public interface TypeAdapterFactory {

  /**
   * Returns a type adapter for {@code type}, or null if this factory doesn't
   * support {@code type}.
   用于根据解析器和变量类型来创建 TypeAdapter
   */
  <T> TypeAdapter<T> create(Gson gson, TypeToken<T> type);
}

```

![](https://s2.loli.net/2022/05/09/bsJRNkvFx3CZ6u4.png)



### 如何获取TypeAdapter

```java
TypeAdapter<?> cached = typeTokenCache.get(type == null ? NULL_KEY_SURROGATE : type);
  if (cached != null) {
    return (TypeAdapter<T>) cached;
  }
```

从缓存获取**TypeAdapter**对象，存在者直接返回

```java
FutureTypeAdapter<T> ongoingCall = (FutureTypeAdapter<T>) threadCalls.get(type);
  if (ongoingCall != null) {
    return ongoingCall;
  }
```

通过ThreadLocal缓存TypeAdapter对象，不同的线程使用缓存来解析的时候互不影响。

```java
for (TypeAdapterFactory factory : factories) {
   TypeAdapter<T> candidate = factory.create(this, type);
    if (candidate != null) {
        call.setDelegate(candidate);
        typeTokenCache.put(type, candidate);
        return candidate;
    }
}
```

如果不存在缓存，那么从factories列表里查找，factories是在创建Gson对象时初始化，添加了很多用于创建TypeAdapter对象的TypeAdapterFactory。

### JsonReader/JsonWriter

在Gson中，Java对象与JSON字符串之间的转换是通过字符流来进行操作的。JsonReader继承于Reader用来读取字符，JsonWriter继承于Writer用来写入字符。



#### JsonReader

**进行数据的写入 用于反序列化操作**

- beginObject():将状态数组的状态的第一个位置从EMPTY_DOCUMENT变为NONEMPTY_DOCUMENT，然后将第二个位置变为EMPTY_OBJECT 
- beginArray():将状态数组的状态的第一个位置从EMPTY_DOCUMENT变为NONEMPTY_DOCUMENT，然后将第二个位置变为EMPTY_OBJECT
- endObject :将peek设置为peek_none;将pathNames数组中stackSize位置设置为null
- endArray:将peek设置为peek_none;将pathNames数组中stackSize位置设置为null
- hasNext:通过标识符判断是否还有数据可以读取
- nextName:获取json中对应的key值
- nextString:获取json中对应的String类型的value值
- nextBoolean:获取json中对应的Boolean类型的value值
- nextDouble:获取json中对应的Double类型的value值
- nextLong:获取json中对应的Long类型的value值
- nextInt:获取json中对应的Int类型的value值
- nextUnquotedValue:以字符串形式返回未加引号的值
- nextQuotedValue:以字符串形式返回加引号的值
- peek:根据peek当前的的状态，判断下一个状态是什么
- close():关闭输入流

#### JsonWriter

- beginObject:通过open()写入json是object的起始符号**{**，在写入数据之前需要调用该方法
- endObject:通过clase()写入json是object的结束符号**}** 在写入数据结束后需要调用该方法
- beginArray:通过open()写入json是array的起始符号**[**，在写入数据之前需要调用该方法
- endArray:通过close()写入json是array的结束符号**]**，在数据结束后需要调用该方法
- name:设置deferredName
- writeDeferredName：通过Writer将deferredName值写入
- value:首先判断是否是第一个数据，若不是则需要先写入逗号(,)，然后写入deferredName值，之后写入分号(:),最后写入value值
- nullValue: 写入null

### JsonElement

该类是一个抽象类，代表着json串的某一个元素。这个元素可以是一个Json(JsonObject)、可以是一个数组(JsonArray)、可以是一个Java的基本类(JsonPrimitive)、当然也可以为null(JsonNull);JsonObject,JsonArray,JsonPrimitive，JsonNull都是JsonElement这个抽象类的子类。JsonElement提供了一系列的方法来判断当前的JsonElement。

各个JsonElement的关系可以用如下图表示：

![image](https://s2.loli.net/2022/05/09/ufeZpImHrykPEL7.png)

JsonObject对象可以看成 name/values的集合，而这写values就是一个个JsonElement,他们的结构可以

用如下图表示：

![image](https://s2.loli.net/2022/05/09/aBhHEXKuiyI8qAe.png)





### Gson整体解析原理

1. **Gson**将使用者传入的字符串或对象存入读取器(**JsonReader**)或者写入器(**JsonWriter**)中
2. **Gson**遍历并获取能够处理对应类型的适配器工厂(**TypeAdapterFactory**)
3. 适配器工厂**TypeAdapterFactory**会创建出对应类型的适配器(**TypeAdapter**)
4. **Gson**将阅读器**JsonReader**或写入器**JsonWriter**交给适配器
5. 适配器自行通过业务逻辑操作读取器**JsonReader**或写入器**JsonWriter**，输出需要的结果
6. **Gson**接收此输出，并交给使用者

![](https://s2.loli.net/2022/05/09/oLuXW2y9hnqZzIH.png)

### Gson反射解析机制

![](https://s2.loli.net/2022/05/09/n5HEpNdxXJoVzPU.png)



## Gson解析常见的错误

*Expected BEGIN_ARRAY but was STRING at line 1 column 27*

这种错误一般都是原来是一个字段需要是数组类型，但是事实上给的是””,导致的

**解决办法**

1. 让返回null即可解决问题

2. 用Gson自带的解决方案

```java
  static class GsonError1Deserializer implements JsonDeserializer<GsonError1> {

        @Override
        public GsonError1 deserialize(JsonElement json, Type typeOfT, JsonDeserializationContext context) throws JsonParseException {
            final JsonObject jsonObject = json.getAsJsonObject();

            final JsonElement jsonTitle = jsonObject.get("name");
            final String name = jsonTitle.getAsString();

            JsonElement jsonAuthors = jsonObject.get("authors");

            GsonError1 gsonError1 = new GsonError1();

            if (jsonAuthors.isJsonArray()) {
                GsonError1.AuthorsBean[] authors = context.deserialize(jsonAuthors, GsonError1.AuthorsBean[].class);
                gsonError1.setAuthors(Arrays.asList(authors));
            } else {
                gsonError1.setAuthors(null);
            }
            gsonError1.setName(name);
            return gsonError1;
        }
    }

    static class AuthorDeserializer implements JsonDeserializer {

        @Override
        public Object deserialize(JsonElement json, Type typeOfT, JsonDeserializationContext context) throws JsonParseException {
            final JsonObject jsonObject = json.getAsJsonObject();

            final GsonError1.AuthorsBean author = new GsonError1.AuthorsBean();
            author.setId(jsonObject.get("id").getAsString());
            author.setName(jsonObject.get("name").getAsString());
            return author;
        }
    }
```

```java
   public static void test3() {
        //TODO:
        String json = "{\n" +
                "    \"name\": \"java\",\n" +
                "    \"authors\": \"\"\n" +
                "}";

        GsonBuilder gsonBuilder = new GsonBuilder();

        //注册TypeAdapter
        gsonBuilder.registerTypeAdapter(GsonError1.class, new GsonError1Deserializer());
        gsonBuilder.registerTypeAdapter(GsonError1.AuthorsBean.class, new AuthorDeserializer());

        Gson gson = gsonBuilder.create();
        GsonError1 gsonError1 = gson.fromJson(json, GsonError1.class);

        System.out.println(gsonError1);
    }
```


