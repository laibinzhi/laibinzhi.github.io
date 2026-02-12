---
title: Compose 中的 CompositionLocal 深度解读：原理、性能、实践与避坑
date: 2026-02-13 00:55:26
tags:
  - Android
  - Jetpack Compose
  - Kotlin
categories:
  - Android
---

做 Compose 一段时间后，基本都会接触 `LocalContext`、`LocalDensity`、`LocalLayoutDirection` 这些 API。它们背后是同一套机制：`CompositionLocal`。

在项目里，`CompositionLocal` 很容易被当成“省参数”的快捷方式。前期写起来很快，后期排查问题时依赖路径会变得不透明。下面这篇按工程视角展开，重点聊三件事：它解决什么问题、什么时候值得用、什么时候更适合参数传递。

<!--more-->

## 一，先说结论：CompositionLocal 是什么

`CompositionLocal` 是 Compose 提供的一种“沿着组合树向下传递隐式依赖”的机制。

对比普通参数传递：

- 普通参数：依赖是显式的，函数签名能直接看出来。
- `CompositionLocal`：依赖是隐式的，不在参数里，运行时从最近的 `Provider` 读取。

你可以把它理解成“作用域化的环境变量”，但作用域不是线程，也不是进程，而是 **UI 的 Composition 子树**。

---

## 二，为什么会需要它

先看一个常见场景：

你有一套设计系统 `AppColors`、`AppTypography`、`AppSpacing`，页面树很深。每一层都手动传这些参数会非常啰嗦，而且很多中间层根本不关心这些值。

这时 `CompositionLocal` 的价值就出来了：

1. 依赖是“跨层级的”，但范围只在某个 UI 子树。
2. 中间层不需要“参数透传”。
3. 可以在局部覆盖（override）同一个依赖。

这也是为什么 Material3 内部大量使用 `CompositionLocal`（如主题、文本样式、涟漪配置等）。

---

## 三，核心 API（定义、提供、读取）

### 3.1 定义 Local

```kotlin
val LocalAnalytics = compositionLocalOf<Analytics> {
    error("No Analytics provided")
}
```

如果希望在没提供时立刻暴露问题，通常会直接用 `error(...)`。

### 3.2 在子树里提供值

```kotlin
CompositionLocalProvider(
    LocalAnalytics provides analytics
) {
    AppContent()
}
```

也可以一次提供多个：

```kotlin
CompositionLocalProvider(
    LocalAnalytics provides analytics,
    LocalLogger provides logger
) {
    AppContent()
}
```

### 3.3 读取值

```kotlin
@Composable
fun TrackableButton(onClick: () -> Unit) {
    val analytics = LocalAnalytics.current
    Button(
        onClick = {
            analytics.log("trackable_button_click")
            onClick()
        }
    ) {
        Text("Click")
    }
}
```

读取入口就是 `.current`。

---

## 四，`compositionLocalOf` vs `staticCompositionLocalOf`

这是 `CompositionLocal` 最容易被忽略但最关键的性能点。

### `compositionLocalOf`

- 会追踪读取位置（read tracking）。
- 当值变化时，只重组真正读取该 Local 的 Composable。
- 适合“可能变化”的值。

### `staticCompositionLocalOf`

- 不追踪读取位置。
- 当值变化时，`Provider` 下整棵内容都会重组。
- 适合“几乎不变”的值（例如应用级单例配置）。

示例：

```kotlin
val LocalImageLoader = staticCompositionLocalOf<ImageLoader> {
    error("No ImageLoader provided")
}
```

如果 `ImageLoader` 在应用生命周期里不会变，`staticCompositionLocalOf` 更合适。

---

## 五，重组行为到底怎么发生

把它分成两步理解：

1. Composable 在执行时读取了 `LocalX.current`，Compose 记录这次读取（`compositionLocalOf` 情况下）。
2. 当 `LocalX` 新值被 `Provider` 提供时，Compose 根据读取记录触发对应节点重组。

这里有两个实战注意点：

1. 频繁变化的值放到 `CompositionLocal`，会扩大重组影响面。
2. 即使是稳定对象，如果你每次都创建新实例，也会导致不必要重组。

实践里更常见的做法：

- 对 Local value 尽量保持引用稳定（必要时 `remember`）。
- 真正高频变化的业务状态，优先放在参数或状态容器中显式传递。

---

## 六，什么时候该用，什么时候别用

### 6.1 推荐使用场景

1. **设计系统令牌**：颜色、字体、间距、圆角、阴影。
2. **平台环境信息**：`Context`、`Density`、布局方向、配置。
3. **跨层但“界面环境型”依赖**：埋点器、Toast/Snackbar 分发器、权限请求协调器（谨慎）。
4. **预览/测试替换点**：在 Preview/Test 中覆盖实现。

### 6.2 不推荐场景

1. **业务核心状态**（用户信息、订单状态、播放进度等）。
2. **复杂业务对象滥用全局透传**（最后没人知道依赖从哪里来）。
3. **本应通过参数表达的组件契约**（损害可读性和可复用性）。

快速判断方式：

- 如果它是“UI 环境”，考虑 `CompositionLocal`。
- 如果它是“业务数据”，优先显式参数 + 状态提升。

---

## 七，一个完整可落地示例：自定义 Design System

```kotlin
@Immutable
data class AppSpacing(
    val xs: Dp = 4.dp,
    val sm: Dp = 8.dp,
    val md: Dp = 16.dp,
    val lg: Dp = 24.dp
)

val LocalSpacing = staticCompositionLocalOf { AppSpacing() }

@Composable
fun AppTheme(
    darkTheme: Boolean,
    content: @Composable () -> Unit
) {
    val spacing = remember { AppSpacing() }

    CompositionLocalProvider(
        LocalSpacing provides spacing
    ) {
        MaterialTheme(
            colorScheme = if (darkTheme) darkColorScheme() else lightColorScheme(),
            content = content
        )
    }
}
```

页面中读取：

```kotlin
@Composable
fun ProfileCard() {
    val spacing = LocalSpacing.current
    Card(
        modifier = Modifier.padding(spacing.md)
    ) {
        Column(
            modifier = Modifier.padding(spacing.lg)
        ) {
            Text("Laibinzhi")
            Spacer(Modifier.height(spacing.sm))
            Text("Android Developer")
        }
    }
}
```

这个模式的优势：

- 参数更干净，避免层层透传。
- 主题切换或品牌换肤时，改动集中。
- 预览里可局部覆盖，验证边界场景更方便。

---

## 八，测试与预览里的用法

`CompositionLocal` 最大的工程价值之一，是让你在测试时替换依赖而不改业务代码。

```kotlin
@Composable
fun FakeAnalyticsProvider(content: @Composable () -> Unit) {
    val fake = remember { FakeAnalytics() }
    CompositionLocalProvider(LocalAnalytics provides fake) {
        content()
    }
}
```

在 `@Preview` 或 UI Test 包裹后，可以验证：

1. 组件是否按预期读取 Local。
2. 不同依赖实现（真实/假实现）下行为是否一致。

---

## 九，常见误区与避坑清单

1. **把 `CompositionLocal` 当 Service Locator**：依赖来源不透明，阅读和调试成本飙升。
2. **默认值写成“静默兜底”**：忘记提供时不报错，线上才暴露行为异常。建议关键依赖用 `error("No xxx provided")`。
3. **高频变化值塞进 Local**：重组范围难控，性能抖动。
4. **在深层组件偷偷读取过多 Local**：组件复用性下降，脱离当前主题/运行环境后难以单独使用。
5. **忽略作用域覆盖规则**：内层 `CompositionLocalProvider` 会覆盖外层同名 Local，调试时要先看“最近 Provider 是谁”。

---

## 十，和 DI（Hilt/Koin）是什么关系

它们不是替代关系，而是职责不同：

- DI：解决对象创建与生命周期管理（对象从哪里来）。
- `CompositionLocal`：解决对象在 UI 子树中的消费方式（UI 如何拿到）。

一个合理分工是：

1. 用 DI 在应用层拿到对象（如 `Analytics`、`ImageLoader`）。
2. 在根 Composable 通过 `CompositionLocalProvider` 注入到 UI 环境。
3. 下层 UI 在需要处通过 `.current` 读取。

---

## 十一，落地建议（可作为团队约定）

1. Local 命名统一用 `LocalXxx`，并收敛到 `ui/local` 或 `designsystem` 包。
2. 对“几乎不变”的对象优先 `staticCompositionLocalOf`。
3. 对可能变化且需要精准重组的对象用 `compositionLocalOf`。
4. 业务状态默认走参数，禁止“为了省事”塞 Local。
5. 所有关键 Local 默认值使用 `error(...)`，避免静默失败。
6. 代码评审里新增 Local 时，通常会重点看三件事：为什么不能参数传递、作用域应该多大、值变化频率是否会造成重组问题。

---

## 十二，从运行时视角看触发机制（源码级直觉）

如果你想真正理解它为什么会触发重组，可以用这个心智模型：

1. 组合树中的每个作用域，都可以拿到一份当前“环境值映射”（可理解为 `CompositionLocalMap`）。
2. `CompositionLocalProvider` 在进入内容块时，会基于父作用域映射生成一份新的子作用域映射。
3. 读取 `LocalX.current` 时，会从当前作用域映射中取值。
4. 对于 `compositionLocalOf`，读取会被记录到当前重组作用域；值变化时，只让真正读取过它的节点失效并重组。
5. 对于 `staticCompositionLocalOf`，不做读取追踪；值变化时，直接让该 `Provider` 下内容整体重组。

这就是“为什么两种 Local 在值变化时行为不同”的根因。

---

## 十三，作用域覆盖（override）规则

覆盖规则按**就近原则**理解就可以：谁离读取点最近就用谁。

```kotlin
CompositionLocalProvider(LocalContentColor provides Color.Red) {
    Text("A") // 红色

    CompositionLocalProvider(LocalContentColor provides Color.Blue) {
        Text("B") // 蓝色
    }

    Text("C") // 红色
}
```

工程里最常见的用法：

1. 全局根主题提供默认值。
2. 某个功能页按业务需要临时覆盖。
3. 某个组件内部再做一次更细粒度覆盖。

调试时按“最近 Provider 生效”这个顺序往上看，通常就能很快定位问题。

---

## 十四，常见 Local 速查

1. `LocalContext`：当前 `Context`。
2. `LocalDensity`：`Dp`/`Sp` 与像素转换。
3. `LocalLayoutDirection`：LTR/RTL 布局方向。
4. `LocalConfiguration`：屏幕配置（尺寸、字体缩放等）。
5. `LocalView`：当前 Compose 所在 `View`。
6. `LocalInspectionMode`：是否处于 Preview/Inspection 环境。

你平时大量使用的 Material 主题能力，本质也建立在 `CompositionLocal` 机制之上。

---

## 十五，性能与可维护性检查清单

做评审前可以快速过一遍这 8 条：

1. 这个依赖是不是 UI 环境型，而不是业务状态？
2. 能不能先用参数传递表达清楚组件契约？
3. 这个值变化频率高不高？高频就不要放 Local。
4. 是否选择了正确的 API：`compositionLocalOf` / `staticCompositionLocalOf`？
5. Local value 是否保持了引用稳定（避免每次重建）？
6. 默认值是否在缺失时快速失败（`error(...)`）？
7. 是否在测试与预览中提供了可替换实现？
8. 团队是否能从模块结构快速定位 Local 的定义与提供位置？

如果这些问题里有多条回答不清，通常说明这个 Local 的边界还可以再收敛。

---

## 总结

`CompositionLocal` 不是“少写参数”的技巧，而是 Compose 里一套严肃的环境依赖机制。它能让你的 UI 架构更干净，也能在误用时让依赖关系变得隐蔽和脆弱。

用好它的关键只有一句话：**只用在 UI 环境依赖，不用在业务核心状态**。在这个前提下，再结合 `compositionLocalOf` / `staticCompositionLocalOf` 的重组语义做选择，项目就能既优雅又稳定。
