---
title: 从纯 Android 到 KMP + CMP：一次真实迁移的做法和坑点
date: 2026-02-12 11:35:00
tags:
  - Android
  - KMP
  - CMP
  - Kotlin
categories:
  - Android
---

如果你手里是一个已经上线很久的 Android 项目，不要把 KMP/CMP 当成“重写项目”的理由。真正可行的路径是：保留现有 Android 业务节奏，把可共享的部分一点点搬到 shared。

迁移可以拆成三步：先迁数据层，再迁状态层，最后才碰 UI。

---

## 先定一个现实目标

一开始别追“复用率 80%”。这个目标听上去很美，但会逼着你把不该共享的东西硬塞进 shared，最后两端都难受。

更实用的目标是这三个：

- Android 和 iOS 的业务结果一致（成功、失败、重试策略一致）
- 关键页面状态流转一致（加载、空态、错误态一致）
- 迁移过程可以随时停、随时回滚

---

<!--more-->


## 第一步：先动数据层，不动 UI

最先迁的是网络 + 仓库层。这个阶段的原则很简单：Android 页面逻辑先不改，只把数据来源替换成 shared。

项目结构可以先变成这样：

```text
project
├── androidApp          # 现有 Android app，先继续用
├── iosApp              # iOS 壳（后面接入）
└── shared
    ├── model
    ├── network
    └── repository
```

`shared/build.gradle.kts` 先保持最小可用：

```kotlin
kotlin {
    androidTarget()
    iosX64()
    iosArm64()
    iosSimulatorArm64()

    sourceSets {
        val commonMain by getting {
            dependencies {
                implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.8.1")
                implementation("io.ktor:ktor-client-core:2.3.12")
                implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.7.1")
            }
        }

        val androidMain by getting {
            dependencies {
                implementation("io.ktor:ktor-client-okhttp:2.3.12")
            }
        }

        val iosMain by creating {
            dependsOn(commonMain)
            dependencies {
                implementation("io.ktor:ktor-client-darwin:2.3.12")
            }
        }

        getByName("iosX64Main").dependsOn(iosMain)
        getByName("iosArm64Main").dependsOn(iosMain)
        getByName("iosSimulatorArm64Main").dependsOn(iosMain)
    }
}
```

这里最容易漏的是 `iosMain`。不建它，后面 iOS 三套 sourceSet 配置会写到怀疑人生。

---

## 第二步：先统一错误语义，再说“多端一致”

很多迁移失败不是因为技术本身，而是 Android 和 iOS 的错误定义各自为政。

建议 shared 里先把错误语义钉死：

```kotlin
sealed interface AppError {
    data object Network : AppError
    data object Unauthorized : AppError
    data class Server(val code: Int, val message: String? = null) : AppError
    data class Unknown(val cause: Throwable) : AppError
}

sealed interface AppResult<out T> {
    data class Success<T>(val data: T) : AppResult<T>
    data class Failure(val error: AppError) : AppResult<Nothing>
}
```

仓库层统一返回 `AppResult`，不要把原生异常往上抛：

```kotlin
class UserRepository(private val api: UserApi) {

    suspend fun fetchProfile(): AppResult<UserProfile> = runCatching {
        api.profile()
    }.fold(
        onSuccess = { AppResult.Success(it) },
        onFailure = { throwable -> AppResult.Failure(throwable.toAppError()) }
    )
}
```

这个改动看起来小，但它会直接减少“同一个错误，双端两个文案和两个处理逻辑”的情况。

---

## 第三步：把 Android 的 ViewModel 思路抽成 shared StateHolder

这一步是迁移里的转折点。

如果你还在 Android 端单独维护一套 `ViewModel` 逻辑，而 shared 只提供数据，那你其实只做了“网络层复用”。

一般先把状态机抽成 shared：

```kotlin
data class ProfileState(
    val loading: Boolean = false,
    val userName: String = "",
    val error: AppError? = null
)

class ProfileStateHolder(
    private val repo: UserRepository,
    private val scope: CoroutineScope
) {
    private val _state = MutableStateFlow(ProfileState())
    val state: StateFlow<ProfileState> = _state.asStateFlow()

    fun load() {
        scope.launch {
            _state.update { it.copy(loading = true, error = null) }
            when (val result = repo.fetchProfile()) {
                is AppResult.Success -> _state.update {
                    it.copy(loading = false, userName = result.data.name)
                }
                is AppResult.Failure -> _state.update {
                    it.copy(loading = false, error = result.error)
                }
            }
        }
    }
}
```

Android 端先消费这个状态；等 iOS 接入时，iOS 也走同一个状态流。这样迁移的收益才会真正显现出来。

---

## 什么时候开始用 CMP 比较稳

别把第一个 CMP 页面选在登录、支付、下单这些链路上。建议从“低风险 + 状态简单”的页面开始，比如：

- 设置页
- 纯展示详情页
- 简单列表页

一个最小 CMP 页面大概这样：

```kotlin
@Composable
fun ProfileScreen(holder: ProfileStateHolder) {
    val uiState by holder.state.collectAsState()

    when {
        uiState.loading -> CircularProgressIndicator()
        uiState.error != null -> Text("Load failed")
        else -> Text("Hello, ${uiState.userName}")
    }
}
```

先跑通 1 个页面，再决定要不要扩大 CMP 覆盖面，这样风险最低。

---

## 迁移里最容易复现的坑

### 1) 把平台能力硬抽到 shared

比如权限、推送、支付 SDK。如果硬抽，很快就会陷入 `expect/actual` 爆炸。建议这些继续放在平台层，只把业务决策结果交给 shared。

### 2) shared 里默认跑主线程

重解析 JSON、批量 DB 写入不切 dispatcher，两端一起卡。这个问题非常常见，而且第一次排查很难想到是 shared 造成的。

### 3) iOS 接 Flow 时没处理生命周期

订阅了不取消，页面销毁后还在收数据。建议做一层 `watch + close` 封装，把取消行为显式化。

### 4) 一次迁太多

同时迁网络、数据库、UI，最后出了问题没人说得清是哪里坏了。建议每次只迁一个业务点，保持可回退。

---

## 给纯 Android 团队的最小迁移清单

按这个顺序做，基本不会翻车：

1. 建立 `shared`，只放模型和 1 个接口请求
2. Android 先接 shared repository，不改页面
3. 抽一个 StateHolder，替换 Android 里同类 ViewModel 逻辑
4. iOS 接入同一个 StateHolder
5. 选 1 个低风险页面试 CMP
6. 观察一轮线上数据，再决定是否扩大范围

---

## 结尾

KMP + CMP 这件事，不难在“会不会写代码”，难在“能不能控制迁移节奏”。

从纯 Android 转过来，最怕的不是慢，而是乱。只要你能保证每一步都可验证、可回滚，迁移就能稳稳推进。
