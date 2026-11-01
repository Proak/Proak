extends Node3D
# The Unfinished Confession: original programmatic 3D vertical slice.
# All scene meshes and sound in this prototype are created for this project.

const LEVEL_END: float = 116.0
const STATION_Z = [12.5, 35.0, 59.0, 83.0, 108.5]
const GATE_Z = [20.0, 43.0, 67.0, 91.0]
const TITLES = ["未被选择的相片", "呼吸登记处", "观察自己的观察", "第三次忏悔", "没有最终一页"]
const CHAPTERS = ["序  ·  未被记录", "一  ·  拂晓", "二  ·  正午", "三  ·  黄昏", "尾声  ·  未完成"]
const PAGES = [
    ["照片已经被拍下，却尚未有人提出索取。", "你以为只有两种选择：保存，或者遗忘。", "但在你决定之前，建筑已经为这个问题修建了一扇门。"],
    ["你的呼吸并不等待你的许可。", "当你开始倾听它，重复便被赋予了新的名字。", "记录员写下：第一次忏悔，与痛苦无关。"],
    ["有人对着镜子说：我看见了自己。", "镜子回答：我看见你正在看见自己。", "下一面镜子没有显示图像。它只显示可能存在的下一面镜子。"],
    ["你曾经把重复次数当作罪恶的深度。", "档案显示：同样的痛苦，可能对应不同的认知位置。", "你无法查明自己的坐标；但你知道自己正在尝试查明。"],
    ["终点没有被找到。", "门外并不是答案，而是一段还没有发生的普通生活。", "你无需认定它有意义，也无需证明它没有意义。", "记录终止。可能性没有终止。"]
]
const COLORS = [Color(0.48,0.55,0.57),Color(0.63,0.53,0.44),Color(0.59,0.58,0.51),Color(0.44,0.47,0.53),Color(0.70,0.68,0.59)]

var current_stage: int = 0
var player: CharacterBody3D
var camera: Camera3D
var gates: Array[StaticBody3D] = []
var stations: Array[Node3D] = []
var sign_text: Label3D
var hud_title: Label
var hud_hint: Label
var hud_subtitle: Label
var dialog_panel: PanelContainer
var dialog_label: Label
var dialog_chapter: Label
var overlay: ColorRect
var progress_bar: ProgressBar
var ambience: AudioStreamPlayer
var hum: AudioStreamPlayer
var sfx: AudioStreamPlayer
var dialog_active: bool = false
var dialog_step: int = 0
var first_input: bool = true
var observation: float = 0.0
var last_near: int = -1
var ending: bool = false
var elapsed: float = 0.0
var original_mouse: int = Input.MOUSE_MODE_CAPTURED
var font: Font
# Gameplay v0.2: tangible valve sequence, optional evidence, recoverable chase.
const VALVE_ANSWER := [0, 1, 0] # Lower pressure, then higher, then lower.
var valves: Array[Node3D] = []
var valve_step: int = 0
var valve_solved: bool = false
var evidence: Array[Node3D] = []
var evidence_found: Dictionary = {}
var pursuer: Node3D
var pursuer_active: bool = false
var chase_attempts: int = 0

func _ready() -> void:
    _set_up_input()
    _set_up_world()
    _set_up_player()
    _build_gameplay_props()
    _set_up_ui()
    _set_up_audio()
    Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
    _set_hud_subtitle("拂晓的光落在走廊里。每一面墙都等待被注意到。")

func _set_up_input() -> void:
    var mapping := {"interact": KEY_E, "move_forward": KEY_W, "move_back": KEY_S, "move_left": KEY_A, "move_right": KEY_D}
    for name in mapping.keys():
        if not InputMap.has_action(name):
            InputMap.add_action(name)
        var key := InputEventKey.new()
        key.physical_keycode = mapping[name]
        InputMap.action_add_event(name,key)

func _set_up_world() -> void:
    var world := WorldEnvironment.new()
    var env := Environment.new()
    env.background_mode = Environment.BG_COLOR
    env.background_color = Color(0.042,0.047,0.055)
    env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    env.ambient_light_color = Color(0.37,0.40,0.48)
    env.ambient_light_energy = 0.24
    env.fog_enabled = true
    env.fog_light_color = Color(0.10,0.105,0.119)
    env.fog_density = 0.014
    world.environment = env
    add_child(world)
    var tex_concrete: Texture2D = load("res://assets/textures/concrete.png")
    var tex_dark: Texture2D = load("res://assets/textures/dark_stone.png")
    var concrete: StandardMaterial3D = _material(Color(0.58,0.59,0.58),tex_concrete)
    var floor_mat: StandardMaterial3D = _material(Color(0.34,0.36,0.38),tex_dark)
    var brass: StandardMaterial3D = _material(Color(0.58,0.42,0.27))
    brass.metallic = 0.64
    brass.roughness = 0.38
    var black: StandardMaterial3D = _material(Color(0.035,0.043,0.052))
    _block("Floor", Vector3(0,-0.3,57),Vector3(7.4,.6,117),floor_mat,true)
    _block("Ceiling", Vector3(0,4.8,57),Vector3(7.4,.36,117),concrete,true)
    _block("Left wall",Vector3(-3.75,2.3,57),Vector3(.38,5,117),concrete,true)
    _block("Right wall",Vector3(3.75,2.3,57),Vector3(.38,5,117),concrete,true)
    for z in [0.0,20.0,43.0,67.0,91.0,116.0]:
        _block("Expansion seam",Vector3(0,-.005,z),Vector3(7.0,.014,.05),black,false)
    for i in range(5):
        _decorate_zone(i, [0.0,21.0,44.0,68.0,92.0][i], [19.0,42.0,66.0,90.0,115.0][i], concrete, brass, black)
    for i in range(4):
        var body := _block("GATE_%02d"%i,Vector3(0,2.0,GATE_Z[i]),Vector3(6.9,4.1,.48),black,true)
        gates.append(body)
        _block("Gate number",Vector3(0,4.20,GATE_Z[i]-.34),Vector3(2.1,.065,.06),brass,false)
    for i in range(STATION_Z.size()):
        var station := Node3D.new()
        station.name = "Station_%02d"%i
        station.position = Vector3(0,0,STATION_Z[i])
        add_child(station)
        stations.append(station)
        _station_prop(station,i,brass,black)
    for i in range(5):
        var posz: float = [10.0,32.0,56.0,80.0,104.0][i]
        _add_lamp(Vector3(0,4.52,posz), [Color(0.72,0.81,1.0),Color(1,.72,.44),Color(1,.92,.59),Color(.63,.72,.94),Color(.93,.91,.85)][i], [2.2,2.8,2.5,2.3,3.4][i])

func _decorate_zone(index: int, za: float, zb: float, concrete: Material, metal: Material, black: Material) -> void:
    var mid: float = (za+zb)*.5
    if index == 0:
        for j in range(6):
            var z: float = za + 3.0 + j*2.7
            _block("Morning aperture",Vector3(-3.48,3.1,z),Vector3(.06,2.6,.25),metal,false)
            _block("Ray trace",Vector3(-2.9,.012,z+.6),Vector3(1.5,.015,.04),metal,false)
    elif index == 1:
        for j in range(11):
            var z: float = za + 1.4 + j*1.9
            for side in [-1.0,1.0]:
                _block("Archive upright",Vector3(side*2.9,2.3,z),Vector3(.16,3.4,.12),metal,false)
                for shelf in range(3):
                    _block("Archive sheet",Vector3(side*2.98,1.0+shelf*.84,z+.32),Vector3(.55,.12,.55),concrete,false)
    elif index == 2:
        for j in range(7):
            var z: float = za + 2.0 + j*2.7
            for side in [-1.0,1.0]:
                _block("Light slit",Vector3(side*3.40,2.6,z),Vector3(.095,2.5,.16),metal,false)
    elif index == 3:
        for j in range(8):
            var z: float = za + 1.3 + j*2.7
            var x: float = -2.4 if j%2 == 0 else 2.4
            _block("Half column",Vector3(x,1.0,z),Vector3(.85,2.0,.65),concrete,false)
            _block("Column void",Vector3(x,2.04,z),Vector3(.75,.04,.65),black,false)
    else:
        for j in range(9):
            var z: float = za + 2.0+j*2.3
            _block("Perspective ceiling rung",Vector3(0,4.5,z),Vector3(6,.15,.12),metal,false)
        _block("Exit plane",Vector3(0,2,114.9),Vector3(6.9,4,.1),black,false)

func _station_prop(parent: Node3D, index: int, metal: Material, black: Material) -> void:
    var pedestal := _mesh_box("Plinth",Vector3(1.7,1.02,1.1),black)
    pedestal.position = Vector3(0,.51,0)
    parent.add_child(pedestal)
    var top := _mesh_box("Top edge",Vector3(1.9,.08,1.27),metal)
    top.position = Vector3(0,1.05,0)
    parent.add_child(top)
    if index == 0:
        _frame(parent,1.15,1.35,1.16,metal)
    elif index == 1:
        for j in range(7):
            var line := _mesh_box("Breathing register",Vector3(.035,.12+.045*j,.08),metal)
            line.position = Vector3(-.55+j*.18,1.25+(.045*j)/2,0)
            parent.add_child(line)
    elif index == 2:
        for j in range(4):
            _frame(parent,1.35-j*.2,1.5-j*.22,1.2+j*.16,metal)
    elif index == 3:
        for j in range(6):
            var tile := _mesh_box("Confession record",Vector3(1.2-j*.09,.04,.16),metal)
            tile.position = Vector3(0,1.22+j*.11,.11)
            parent.add_child(tile)
    else:
        _frame(parent,1.5,1.85,1.1,metal)
    var text := Label3D.new()
    text.text = TITLES[index]
    text.font_size = 32
    text.pixel_size = .0025
    text.position = Vector3(0,1.86,0)
    text.modulate = Color(0.78,.76,.70)
    text.billboard = BaseMaterial3D.BILLBOARD_ENABLED
    parent.add_child(text)

func _frame(parent: Node3D, width: float, height: float, elevation: float, mat: Material) -> void:
    for side in [-1.0,1.0]:
        var bar := _mesh_box("Frame vertical",Vector3(.05,height,.06),mat)
        bar.position = Vector3(side*width*.5,elevation+height*.5,0)
        parent.add_child(bar)
    for side in [-1.0,1.0]:
        var bar := _mesh_box("Frame horizontal",Vector3(width,.055,.06),mat)
        bar.position = Vector3(0,elevation+height*.5+side*height*.5,0)
        parent.add_child(bar)

func _material(color: Color, texture: Texture2D = null) -> StandardMaterial3D:
    var m := StandardMaterial3D.new()
    m.albedo_color = color
    if texture != null:
        m.albedo_texture = texture
    m.roughness = .93
    m.uv1_triplanar = true
    m.uv1_scale = Vector3(1.7,1.7,1.7)
    return m

func _mesh_box(name: String, size: Vector3, mat: Material) -> MeshInstance3D:
    var mi := MeshInstance3D.new()
    mi.name = name
    var cube := BoxMesh.new()
    cube.size = size
    mi.mesh = cube
    mi.material_override = mat
    return mi

func _block(name: String, pos: Vector3, size: Vector3, mat: Material, solid: bool) -> StaticBody3D:
    var body := StaticBody3D.new()
    body.name = name
    body.position = pos
    add_child(body)
    var mesh := _mesh_box("Visual",size,mat)
    body.add_child(mesh)
    if solid:
        var coll := CollisionShape3D.new()
        var sh := BoxShape3D.new()
        sh.size = size
        coll.shape = sh
        body.add_child(coll)
    return body

func _add_lamp(pos: Vector3, color: Color, intensity: float) -> void:
    var light := OmniLight3D.new()
    light.position = pos
    light.light_color = color
    light.light_energy = intensity
    light.omni_range = 11.5
    light.shadow_enabled = false
    add_child(light)

func _set_up_player() -> void:
    player = CharacterBody3D.new()
    player.name = "Player"
    player.set_script(load("res://scripts/player.gd"))
    player.position = Vector3(0,0,2.5)
    var c := CollisionShape3D.new()
    var capsule := CapsuleShape3D.new()
    capsule.radius = .34
    capsule.height = 1.65
    c.shape = capsule
    c.position = Vector3(0,.82,0)
    player.add_child(c)
    camera = Camera3D.new()
    camera.name = "Camera3D"
    camera.position = Vector3(0,1.45,0)
    camera.current = true
    camera.fov = 72.0
    player.add_child(camera)
    player.rotation.y = PI
    add_child(player)


func _build_gameplay_props() -> void:
    # All proxy geometry is original. UE5 final pass replaces these objects.
    for i in range(2):
        var valve := Node3D.new()
        valve.name = "Valve_Low" if i == 0 else "Valve_High"
        valve.position = Vector3(-2.45 if i == 0 else 2.45,0,30.8 if i == 0 else 39.4)
        add_child(valve)
        var stem := _mesh_box("Valve stem",Vector3(.23,1.12,.23),_material(Color(.38,.32,.25)))
        stem.position = Vector3(0,.58,0)
        valve.add_child(stem)
        var ring := _mesh_box("Valve wheel proxy",Vector3(.72,.16,.72),_material(Color(.73,.45,.23)))
        ring.position = Vector3(0,1.18,0)
        valve.add_child(ring)
        var label := Label3D.new()
        label.text = "LOW / 低压" if i == 0 else "HIGH / 高压"
        label.font_size = 36
        label.pixel_size = .0022
        label.position = Vector3(0,1.58,0)
        label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
        valve.add_child(label)
        valves.append(valve)
    var slips := [Vector3(2.8,0,6.0),Vector3(-2.8,0,52.4),Vector3(2.7,0,78.4)]
    for i in range(slips.size()):
        var page := Node3D.new()
        page.name = "Optional_Evidence_%02d"%i
        page.position = slips[i]
        add_child(page)
        var sheet := _mesh_box("Evidence sheet",Vector3(.48,.05,.35),_material(Color(.81,.74,.57)))
        sheet.position = Vector3(0,.89,0)
        page.add_child(sheet)
        var stand := _mesh_box("Evidence tray",Vector3(.65,.91,.51),_material(Color(.13,.17,.19)))
        stand.position = Vector3(0,.455,0)
        page.add_child(stand)
        evidence.append(page)

func _near_valve() -> int:
    if current_stage != 1 or valve_solved:
        return -1
    for i in range(valves.size()):
        if player.global_position.distance_to(valves[i].global_position+Vector3(0,1.0,0)) < 2.7:
            return i
    return -1

func _turn_valve(index: int) -> void:
    if index == VALVE_ANSWER[valve_step]:
        valve_step += 1
        _sound("click")
        if valve_step >= VALVE_ANSWER.size():
            valve_solved = true
            _sound("reveal")
            _set_hud_subtitle("低压 → 高压 → 低压。门禁已获得供电。")
        else:
            _set_hud_subtitle("压力表指针移到下一档。")
    else:
        valve_step = 0
        _sound("closing")
        _set_hud_subtitle("指针回零。记录纸写着：低压，高压，再低压。")

func _near_evidence() -> int:
    for i in range(evidence.size()):
        if evidence_found.has(i):
            continue
        if player.global_position.distance_to(evidence[i].global_position+Vector3(0,.8,0)) < 2.3:
            return i
    return -1

func _collect_evidence(i: int) -> void:
    evidence_found[i] = true
    evidence[i].queue_free()
    _sound("click")
    var texts := ["未寄出的回执 / 一：已提出的好意，不等于已完成的请求。", "维修谱 / 二：系统必须区分查询与同意。", "录音残片 / 三：我们还没有证明一切都会再次发生。"]
    _set_hud_subtitle(texts[i]+"    (%d/3)"%evidence_found.size())

func _begin_chase() -> void:
    pursuer_active = true
    if pursuer == null:
        pursuer = Node3D.new()
        pursuer.name = "PROXY_Pursuer_NonCombat"
        add_child(pursuer)
        var body := _mesh_box("Raincoat proxy",Vector3(.8,1.75,.55),_material(Color(.105,.13,.14)))
        body.position = Vector3(0,1.0,0)
        pursuer.add_child(body)
        var head := _mesh_box("Hood proxy",Vector3(.61,.52,.52),_material(Color(.052,.06,.065)))
        head.position = Vector3(0,2.07,0)
        pursuer.add_child(head)
    pursuer.position = Vector3(0,0,75.5)
    pursuer.visible = true
    _set_hud_subtitle("远处有人开始沿着同一条走廊奔跑。按住 Shift 奔跑。")

func _advance_chase(delta: float) -> void:
    if not pursuer_active or not is_instance_valid(pursuer):
        return
    if player.global_position.z > 103.0:
        pursuer_active = false
        pursuer.visible = false
        _set_hud_subtitle("门后的脚步声停住了。这里暂时安全。")
        return
    pursuer.position.z += 5.35*delta
    # Limited movement intentionally; v0.2 is NOT full navmesh AI.
    pursuer.position.x = move_toward(pursuer.position.x,player.global_position.x,1.4*delta)
    if pursuer.global_position.distance_to(player.global_position) < 1.65:
        chase_attempts += 1
        pursuer.position = Vector3(0,0,75.5)
        player.position = Vector3(0,1.25,84.9)
        _sound("closing")
        _set_hud_subtitle("你退回到门边。巡查员正在重新寻找你。")

func _label(text: String, size: int, color: Color) -> Label:
    var l := Label.new()
    l.text = text
    l.add_theme_color_override("font_color", color)
    l.add_theme_font_size_override("font_size", size)
    if font != null:
        l.add_theme_font_override("font",font)
    return l

func _set_up_ui() -> void:
    var system := SystemFont.new()
    system.font_names = PackedStringArray(["Noto Sans CJK SC", "Microsoft YaHei", "PingFang SC", "Arial Unicode MS"])
    font = system
    var ui := CanvasLayer.new()
    add_child(ui)
    var root := Control.new()
    root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    root.mouse_filter = Control.MOUSE_FILTER_IGNORE
    ui.add_child(root)
    var top := MarginContainer.new()
    top.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
    top.add_theme_constant_override("margin_left",48)
    top.add_theme_constant_override("margin_top",30)
    root.add_child(top)
    hud_title = _label("序   /   未被记录",17,Color(.78,.79,.77,.92))
    top.add_child(hud_title)
    hud_hint = _label("",17,Color(.84,.81,.72))
    hud_hint.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM)
    hud_hint.position = Vector2(-280,-110)
    hud_hint.custom_minimum_size = Vector2(560,30)
    hud_hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
    root.add_child(hud_hint)
    progress_bar = ProgressBar.new()
    progress_bar.min_value = 0
    progress_bar.max_value = 100
    progress_bar.value = 0
    progress_bar.show_percentage = false
    progress_bar.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM)
    progress_bar.position = Vector2(-120,-78)
    progress_bar.custom_minimum_size = Vector2(240,4)
    progress_bar.visible = false
    root.add_child(progress_bar)
    hud_subtitle = _label("",18,Color(.93,.89,.83))
    hud_subtitle.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
    hud_subtitle.position.y = -58
    hud_subtitle.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
    root.add_child(hud_subtitle)
    var crosshair := _label("·",25,Color(.88,.84,.75,.7))
    crosshair.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
    crosshair.position = Vector2(-4,-12)
    root.add_child(crosshair)
    dialog_panel = PanelContainer.new()
    dialog_panel.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM)
    dialog_panel.position = Vector2(-420,-265)
    dialog_panel.custom_minimum_size = Vector2(840,164)
    var style := StyleBoxFlat.new()
    style.bg_color = Color(.055,.065,.075,.96)
    style.border_color = Color(.52,.47,.39,.8)
    style.set_border_width_all(1)
    style.set_corner_radius_all(5)
    style.set_content_margin_all(25)
    dialog_panel.add_theme_stylebox_override("panel",style)
    var v := VBoxContainer.new()
    v.add_theme_constant_override("separation",10)
    dialog_panel.add_child(v)
    dialog_chapter = _label("",14,Color(.69,.62,.50))
    v.add_child(dialog_chapter)
    dialog_label = _label("",24,Color(.95,.91,.85))
    dialog_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    dialog_label.custom_minimum_size = Vector2(740,65)
    v.add_child(dialog_label)
    var next := _label("E · 继续     Esc · 释放鼠标",13,Color(.57,.60,.62))
    v.add_child(next)
    root.add_child(dialog_panel)
    dialog_panel.visible = false
    overlay = ColorRect.new()
    overlay.color = Color(.65,.66,.62,.0)
    overlay.mouse_filter = Control.MOUSE_FILTER_IGNORE
    overlay.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    root.add_child(overlay)

func _set_up_audio() -> void:
    ambience = AudioStreamPlayer.new()
    ambience.stream = load("res://assets/audio/low_drone.wav")
    ambience.volume_db = -10.0
    add_child(ambience)
    ambience.finished.connect(func(): ambience.play())
    ambience.play()
    hum = AudioStreamPlayer.new()
    hum.stream = load("res://assets/audio/soft_hum.wav")
    hum.volume_db = -27.0
    add_child(hum)
    hum.finished.connect(func(): hum.play())
    hum.play()
    sfx = AudioStreamPlayer.new()
    add_child(sfx)

func _process(delta: float) -> void:
    elapsed += delta
    _advance_chase(delta)
    if ending or dialog_active:
        hud_hint.text = ""
        progress_bar.visible = false
        return
    var paper := _near_evidence()
    if paper >= 0:
        hud_hint.text = "[ E ] 收集可选档案（不影响通关）"
        progress_bar.visible = false
        last_near = -1
        return
    var valve := _near_valve()
    if valve >= 0:
        hud_hint.text = "[ E ] 转动" + ("低压阀" if valve == 0 else "高压阀")
        progress_bar.visible = false
        last_near = -1
        return
    var nearby := _get_nearby_station()
    last_near = nearby
    if nearby == -1:
        hud_hint.text = "WASD 行走  ·  鼠标观察  ·  Esc 切换鼠标" if first_input else ""
        observation = max(0.0,observation-delta*.8)
        progress_bar.visible = false
        return
    first_input = false
    if nearby != current_stage:
        hud_hint.text = "尚未轮到这份记录"
        progress_bar.visible = false
        return
    if current_stage == 1 and not valve_solved:
        hud_hint.text = "门禁无电。走廊两侧有阀门；旧记录纸：低压 → 高压 → 低压。"
        progress_bar.visible = false
        return
    if current_stage == 2:
        hud_hint.text = "按住鼠标右键，观察正在观察的自己"
        if Input.is_mouse_button_pressed(MOUSE_BUTTON_RIGHT):
            observation = min(observation+delta*.43,1.0)
            if observation >= 1.0:
                _begin_dialog()
        else:
            observation = max(observation-delta*.22,0.0)
        progress_bar.value = observation*100.0
        progress_bar.visible = true
        overlay.color.a = observation*.085
    else:
        hud_hint.text = "[ E ] 读取："+TITLES[current_stage]
        progress_bar.visible = false

func _get_nearby_station() -> int:
    for i in range(stations.size()):
        var d: float = player.global_position.distance_to(stations[i].global_position+Vector3(0,0.8,0))
        if d < 3.3:
            return i
    return -1

func _unhandled_input(event: InputEvent) -> void:
    if event is InputEventKey and event.pressed and not event.echo and event.keycode == KEY_ESCAPE:
        Input.mouse_mode = Input.MOUSE_MODE_VISIBLE if Input.mouse_mode == Input.MOUSE_MODE_CAPTURED else Input.MOUSE_MODE_CAPTURED
        get_viewport().set_input_as_handled()
        return
    if event.is_action_pressed("interact"):
        if not dialog_active and not ending and _near_evidence() >= 0:
            _collect_evidence(_near_evidence())
            get_viewport().set_input_as_handled()
            return
        if not dialog_active and not ending and _near_valve() >= 0:
            _turn_valve(_near_valve())
            get_viewport().set_input_as_handled()
            return
        if dialog_active:
            _advance_dialog()
            get_viewport().set_input_as_handled()
        elif last_near == current_stage and current_stage != 2 and not ending and (current_stage != 1 or valve_solved):
            _begin_dialog()
            get_viewport().set_input_as_handled()

func _begin_dialog() -> void:
    dialog_active = true
    dialog_step = 0
    player.set("controls_locked",true)
    dialog_panel.visible = true
    dialog_chapter.text = CHAPTERS[current_stage] + "   /   " + TITLES[current_stage]
    dialog_label.text = PAGES[current_stage][0]
    hud_subtitle.text = ""
    observation = 0.0
    _sound("click")

func _advance_dialog() -> void:
    dialog_step += 1
    if dialog_step < PAGES[current_stage].size():
        dialog_label.text = PAGES[current_stage][dialog_step]
        _sound("click")
        return
    dialog_active = false
    dialog_panel.visible = false
    player.set("controls_locked",false)
    _sound("reveal")
    if current_stage < gates.size():
        gates[current_stage].queue_free()
        var next_index := current_stage+1
        current_stage = next_index
        hud_title.text = CHAPTERS[current_stage]
        if current_stage == 4:
            _begin_chase()
        else:
            _set_hud_subtitle("门已经打开。你没有被告知原因。")
        overlay.color.a = .14
    else:
        ending = true
        pursuer_active = false
        hud_title.text = "记录已结束"
        _set_hud_subtitle("游戏结束 · Esc 释放鼠标 · 关闭窗口退出")
        _sound("closing")

func _sound(name: String) -> void:
    sfx.stream = load("res://assets/audio/%s.wav"%name)
    sfx.play()

func _set_hud_subtitle(text: String) -> void:
    hud_subtitle.text = text
    var tween := create_tween()
    tween.tween_interval(5.0)
    tween.tween_callback(func():
        if is_instance_valid(hud_subtitle) and hud_subtitle.text == text:
            hud_subtitle.text = ""
    )
