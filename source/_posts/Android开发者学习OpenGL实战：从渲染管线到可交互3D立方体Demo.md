---
title: Android开发者学习OpenGL实战：从渲染管线到可交互3D立方体Demo
date: 2023-02-13 01:20:00
tags:
  - Android
  - OpenGL
categories:
  - Android
---

做 Android 久了，迟早会碰到这类需求：实时滤镜、相机特效、动态贴纸、复杂转场、海量图元渲染。到这一步，`Canvas` 和普通属性动画基本就不够用了，OpenGL ES 是绕不开的。

这篇不走“画个三角形就结束”的路线，包含两个 Demo：

1. 入门但不玩具：可交互 3D 立方体（旋转、缩放、光照、深度测试）。
2. 业务落地版本：相机实时滤镜链（OES 纹理 + FBO 多 Pass + 最终上屏）。

两个 Demo 放在一起看，能更直观看到 OpenGL 在 Android 项目里的落地方式，而不只是 API 用法。

<!--more-->

## 一，先把 OpenGL 在 Android 里的角色说清楚

OpenGL ES 在客户端业务里，本质是一个高吞吐的像素处理管线。

常见路径是：

`Camera/Bitmap/视频帧 -> 纹理 -> Shader 计算 -> FrameBuffer -> 屏幕或编码器`

它可以理解成“GPU 版流水线”：CPU 负责组织数据和调度，GPU 负责并行计算像素。Android 开发里，只要进入实时图像处理场景，这套模型基本无法绕开。

## 二，Demo 1：可交互 3D 立方体（入门）

这个 Demo 的目标很直接：把 OpenGL 最核心的几件事一次跑通。

1. `GLSurfaceView + Renderer` 的线程模型。
2. MVP 矩阵变换。
3. Vertex/Fragment Shader 的配合。
4. 深度测试和基础光照。
5. 手势事件安全地投递到 GL 线程。

### 2.1 目录结构

```text
app/src/main/java/com/example/glcube/
  MainActivity.kt
  CubeSurfaceView.kt
  CubeRenderer.kt
  Cube.kt
  ShaderUtils.kt
```

### 2.2 Activity 和 GLSurfaceView

```kotlin
class MainActivity : AppCompatActivity() {

    private lateinit var glView: CubeSurfaceView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        glView = CubeSurfaceView(this)
        setContentView(glView)
    }

    override fun onResume() {
        super.onResume()
        glView.onResume()
    }

    override fun onPause() {
        glView.onPause()
        super.onPause()
    }
}
```

`CubeSurfaceView` 里最关键的是：触摸在主线程，渲染在 GL 线程，参数修改统一走 `queueEvent`。

```kotlin
class CubeSurfaceView(context: Context) : GLSurfaceView(context) {

    private val renderer = CubeRenderer()
    private var lastX = 0f
    private var lastY = 0f

    private val scaleDetector = ScaleGestureDetector(context,
        object : ScaleGestureDetector.SimpleOnScaleGestureListener() {
            override fun onScale(detector: ScaleGestureDetector): Boolean {
                queueEvent { renderer.zoomBy(detector.scaleFactor) }
                return true
            }
        }
    )

    init {
        setEGLContextClientVersion(2)
        setRenderer(renderer)
        renderMode = RENDERMODE_CONTINUOUSLY
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        scaleDetector.onTouchEvent(event)

        if (!scaleDetector.isInProgress) {
            when (event.actionMasked) {
                MotionEvent.ACTION_DOWN -> {
                    lastX = event.x
                    lastY = event.y
                }
                MotionEvent.ACTION_MOVE -> {
                    val dx = event.x - lastX
                    val dy = event.y - lastY
                    queueEvent { renderer.rotateBy(dy * 0.5f, dx * 0.5f) }
                    lastX = event.x
                    lastY = event.y
                }
            }
        }
        return true
    }
}
```

### 2.3 Renderer：矩阵、相机、每帧绘制

```kotlin
class CubeRenderer : GLSurfaceView.Renderer {

    private lateinit var cube: Cube

    private val projection = FloatArray(16)
    private val view = FloatArray(16)
    private val model = FloatArray(16)
    private val mv = FloatArray(16)
    private val mvp = FloatArray(16)

    @Volatile private var angleX = 20f
    @Volatile private var angleY = 30f
    @Volatile private var cameraDistance = 5f

    override fun onSurfaceCreated(gl: GL10?, config: EGLConfig?) {
        GLES20.glClearColor(0.05f, 0.06f, 0.08f, 1f)
        GLES20.glEnable(GLES20.GL_DEPTH_TEST)
        GLES20.glEnable(GLES20.GL_CULL_FACE)
        cube = Cube()
    }

    override fun onSurfaceChanged(gl: GL10?, width: Int, height: Int) {
        GLES20.glViewport(0, 0, width, height)
        Matrix.perspectiveM(projection, 0, 45f, width.toFloat() / height, 0.1f, 100f)
    }

    override fun onDrawFrame(gl: GL10?) {
        GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT or GLES20.GL_DEPTH_BUFFER_BIT)

        Matrix.setLookAtM(view, 0, 0f, 0f, cameraDistance, 0f, 0f, 0f, 0f, 1f, 0f)
        Matrix.setIdentityM(model, 0)
        Matrix.rotateM(model, 0, angleX, 1f, 0f, 0f)
        Matrix.rotateM(model, 0, angleY, 0f, 1f, 0f)

        Matrix.multiplyMM(mv, 0, view, 0, model, 0)
        Matrix.multiplyMM(mvp, 0, projection, 0, mv, 0)

        cube.draw(mvp, mv)
    }

    fun rotateBy(dx: Float, dy: Float) {
        angleX += dx
        angleY += dy
    }

    fun zoomBy(scaleFactor: Float) {
        cameraDistance = (cameraDistance / scaleFactor).coerceIn(2.5f, 12f)
    }
}
```

### 2.4 Cube + Shader（带基础光照）

这里保留核心代码：顶点法线、MVP/MV 矩阵、漫反射。

```kotlin
class Cube {

    private val program: Int
    private val vertexBuffer: FloatBuffer
    private val normalBuffer: FloatBuffer
    private val indexBuffer: ShortBuffer

    private val aPosition: Int
    private val aNormal: Int
    private val uMvp: Int
    private val uMv: Int
    private val uLightDir: Int
    private val uColor: Int

    private val vertices = floatArrayOf(
        -1f, 1f, 1f,  -1f, -1f, 1f,  1f, -1f, 1f,  1f, 1f, 1f,
         1f, 1f, -1f,  1f, -1f, -1f, -1f, -1f, -1f, -1f, 1f, -1f,
        -1f, 1f, -1f, -1f, -1f, -1f, -1f, -1f, 1f, -1f, 1f, 1f,
         1f, 1f, 1f,   1f, -1f, 1f,   1f, -1f, -1f, 1f, 1f, -1f,
        -1f, 1f, -1f, -1f, 1f, 1f,   1f, 1f, 1f,   1f, 1f, -1f,
        -1f, -1f, 1f, -1f, -1f, -1f, 1f, -1f, -1f, 1f, -1f, 1f
    )

    private val normals = floatArrayOf(
         0f, 0f, 1f, 0f, 0f, 1f, 0f, 0f, 1f, 0f, 0f, 1f,
         0f, 0f, -1f, 0f, 0f, -1f, 0f, 0f, -1f, 0f, 0f, -1f,
        -1f, 0f, 0f, -1f, 0f, 0f, -1f, 0f, 0f, -1f, 0f, 0f,
         1f, 0f, 0f, 1f, 0f, 0f, 1f, 0f, 0f, 1f, 0f, 0f,
         0f, 1f, 0f, 0f, 1f, 0f, 0f, 1f, 0f, 0f, 1f, 0f,
         0f, -1f, 0f, 0f, -1f, 0f, 0f, -1f, 0f, 0f, -1f, 0f
    )

    private val indices = shortArrayOf(
        0, 1, 2, 0, 2, 3,
        4, 5, 6, 4, 6, 7,
        8, 9, 10, 8, 10, 11,
        12, 13, 14, 12, 14, 15,
        16, 17, 18, 16, 18, 19,
        20, 21, 22, 20, 22, 23
    )

    init {
        vertexBuffer = ByteBuffer.allocateDirect(vertices.size * 4)
            .order(ByteOrder.nativeOrder())
            .asFloatBuffer().put(vertices).apply { position(0) }

        normalBuffer = ByteBuffer.allocateDirect(normals.size * 4)
            .order(ByteOrder.nativeOrder())
            .asFloatBuffer().put(normals).apply { position(0) }

        indexBuffer = ByteBuffer.allocateDirect(indices.size * 2)
            .order(ByteOrder.nativeOrder())
            .asShortBuffer().put(indices).apply { position(0) }

        val vertexShader = """
            attribute vec4 aPosition;
            attribute vec3 aNormal;
            uniform mat4 uMvpMatrix;
            uniform mat4 uMvMatrix;
            uniform vec3 uLightDir;
            varying float vLight;

            void main() {
                vec3 n = normalize((uMvMatrix * vec4(aNormal, 0.0)).xyz);
                float diffuse = max(dot(n, normalize(uLightDir)), 0.0);
                vLight = 0.25 + 0.75 * diffuse;
                gl_Position = uMvpMatrix * aPosition;
            }
        """.trimIndent()

        val fragmentShader = """
            precision mediump float;
            uniform vec4 uColor;
            varying float vLight;

            void main() {
                gl_FragColor = vec4(uColor.rgb * vLight, uColor.a);
            }
        """.trimIndent()

        program = ShaderUtils.createProgram(vertexShader, fragmentShader)
        aPosition = GLES20.glGetAttribLocation(program, "aPosition")
        aNormal = GLES20.glGetAttribLocation(program, "aNormal")
        uMvp = GLES20.glGetUniformLocation(program, "uMvpMatrix")
        uMv = GLES20.glGetUniformLocation(program, "uMvMatrix")
        uLightDir = GLES20.glGetUniformLocation(program, "uLightDir")
        uColor = GLES20.glGetUniformLocation(program, "uColor")
    }

    fun draw(mvp: FloatArray, mv: FloatArray) {
        GLES20.glUseProgram(program)

        GLES20.glEnableVertexAttribArray(aPosition)
        GLES20.glVertexAttribPointer(aPosition, 3, GLES20.GL_FLOAT, false, 12, vertexBuffer)

        GLES20.glEnableVertexAttribArray(aNormal)
        GLES20.glVertexAttribPointer(aNormal, 3, GLES20.GL_FLOAT, false, 12, normalBuffer)

        GLES20.glUniformMatrix4fv(uMvp, 1, false, mvp, 0)
        GLES20.glUniformMatrix4fv(uMv, 1, false, mv, 0)
        GLES20.glUniform3f(uLightDir, 0.5f, 0.8f, 1.0f)
        GLES20.glUniform4f(uColor, 0.15f, 0.75f, 0.95f, 1f)

        GLES20.glDrawElements(GLES20.GL_TRIANGLES, indices.size, GLES20.GL_UNSIGNED_SHORT, indexBuffer)

        GLES20.glDisableVertexAttribArray(aPosition)
        GLES20.glDisableVertexAttribArray(aNormal)
    }
}
```

如果这一套能够跑通，OpenGL 的基本功已经过了第一关。

## 三，Demo 2：业务落地版相机实时滤镜链（有难度）

下面这个是我更建议在业务中练的 Demo。因为它直接对应“拍摄页实时预览 + 滤镜 + 导出”的典型需求。

### 3.1 业务目标

1. CameraX 预览帧进 GPU。
2. 使用 `samplerExternalOES` 采样相机纹理。
3. 经过 2 个离屏 Pass（磨皮/锐化可替换）。
4. 最终结果上屏，同时可复用到 MediaCodec 编码输入。

### 3.2 渲染链路

```text
CameraX -> SurfaceTexture(OES) -> Pass1(FBO A) -> Pass2(FBO B) -> Screen
```

这条链路最关键的点：

1. 第一段必须是 OES 纹理，普通 `sampler2D` 不能直接采相机流。
2. 中间处理统一落到 2D 纹理，后续 Pass 才能自由组合。
3. 所有 OpenGL 调用必须在同一个 GL 线程和上下文里。

### 3.3 关键类设计

```kotlin
class CameraFilterRenderer : GLSurfaceView.Renderer, SurfaceTexture.OnFrameAvailableListener {

    private var oesTexId = 0
    private lateinit var cameraSurfaceTexture: SurfaceTexture

    private lateinit var passOesTo2D: GlProgram
    private lateinit var passBlur: GlProgram
    private lateinit var passSharpen: GlProgram
    private lateinit var passScreen: GlProgram

    private lateinit var fboA: FrameBuffer
    private lateinit var fboB: FrameBuffer

    @Volatile private var frameAvailable = false

    override fun onSurfaceCreated(gl: GL10?, config: EGLConfig?) {
        oesTexId = GlTex.createOesTexture()
        cameraSurfaceTexture = SurfaceTexture(oesTexId).apply {
            setOnFrameAvailableListener(this@CameraFilterRenderer)
        }

        passOesTo2D = GlProgram(VS_FULL_SCREEN, FS_OES)
        passBlur = GlProgram(VS_FULL_SCREEN, FS_BLUR)
        passSharpen = GlProgram(VS_FULL_SCREEN, FS_SHARPEN)
        passScreen = GlProgram(VS_FULL_SCREEN, FS_2D)

        bindCamera(cameraSurfaceTexture)
    }

    override fun onSurfaceChanged(gl: GL10?, width: Int, height: Int) {
        GLES20.glViewport(0, 0, width, height)
        fboA = FrameBuffer(width, height)
        fboB = FrameBuffer(width, height)
    }

    override fun onFrameAvailable(surfaceTexture: SurfaceTexture?) {
        frameAvailable = true
    }

    override fun onDrawFrame(gl: GL10?) {
        if (frameAvailable) {
            cameraSurfaceTexture.updateTexImage()
            frameAvailable = false
        }

        // Pass1: OES -> FBO A
        fboA.bind()
        passOesTo2D.drawOes(oesTexId)

        // Pass2: A -> FBO B (高斯或双边滤波)
        fboB.bind()
        passBlur.draw2D(fboA.texId)

        // Pass3: B -> A (锐化 / 细节增强)
        fboA.bind()
        passSharpen.draw2D(fboB.texId)

        // Final: A -> Screen
        FrameBuffer.unbind()
        passScreen.draw2D(fboA.texId)
    }
}
```

### 3.4 OES 片元着色器（相机首帧）

```glsl
#extension GL_OES_EGL_image_external : require
precision mediump float;
varying vec2 vTexCoord;
uniform samplerExternalOES uTexture;

void main() {
    gl_FragColor = texture2D(uTexture, vTexCoord);
}
```

### 3.5 一个可直接替换的锐化片元 Shader

```glsl
precision mediump float;
varying vec2 vTexCoord;
uniform sampler2D uTexture;
uniform vec2 uTexel; // (1.0/width, 1.0/height)

void main() {
    vec3 c = texture2D(uTexture, vTexCoord).rgb;
    vec3 up = texture2D(uTexture, vTexCoord + vec2(0.0, uTexel.y)).rgb;
    vec3 down = texture2D(uTexture, vTexCoord - vec2(0.0, uTexel.y)).rgb;
    vec3 left = texture2D(uTexture, vTexCoord - vec2(uTexel.x, 0.0)).rgb;
    vec3 right = texture2D(uTexture, vTexCoord + vec2(uTexel.x, 0.0)).rgb;

    vec3 edge = (up + down + left + right - 4.0 * c);
    vec3 result = c - 0.35 * edge;
    gl_FragColor = vec4(result, 1.0);
}
```

### 3.6 这个 Demo 在业务里最常踩的坑

1. 方向错乱：相机纹理坐标和屏幕坐标是两套系，通常要配合 `SurfaceTexture.getTransformMatrix()`。
2. 画面偶发卡顿：`updateTexImage()` 调用节奏不对，或 CPU 侧参数频繁分配对象。
3. 黑屏：FBO 没绑定完整，或者纹理尺寸和 Viewport 不一致。
4. 发热明显：Pass 太多、分辨率拉满，建议在预览态降采样，导出态再开高质量。

## 四，线上可用性的几个建议

只给实用结论：

1. 滤镜参数不要直接改全局变量，统一做“参数快照”，一帧只读一次，避免撕裂。
2. Shader program、VBO、FBO 在 `onSurfaceCreated/onSurfaceChanged` 分层创建，避免每帧分配。
3. 给每个 Pass 打 GPU 时间戳或至少打帧耗时，先定位瓶颈，再谈优化。
4. 对中低端机做策略降级：关闭高阶滤镜、降分辨率、降帧率，比硬顶稳定。

## 五，小结

第一个 Demo 解决的是“我能不能把 OpenGL 跑起来并理解基本概念”；第二个 Demo 解决的是“这套东西能不能放进业务，并在真实机型上跑稳”。

如果要在 Android 上长期做图形相关开发，后者更重要。因为线上问题通常不是 shader 会不会写，而是链路怎么设计、线程怎么管理、性能怎么兜底。
