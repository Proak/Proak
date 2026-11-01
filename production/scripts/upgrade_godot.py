from pathlib import Path
root=Path(__file__).resolve().parents[2]
g=(root/'game/scripts/main.gd'); s=g.read_text()
s=s.replace('var font: Font\n','''var font: Font
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
''')
s=s.replace('    _set_up_player()\n    _set_up_ui()', '    _set_up_player()\n    _build_gameplay_props()\n    _set_up_ui()')
insert='''
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
'''
s=s.replace('func _label(text: String, size: int, color: Color) -> Label:',insert+'\nfunc _label(text: String, size: int, color: Color) -> Label:')
s=s.replace('    elapsed += delta\n    if ending or dialog_active:', '    elapsed += delta\n    _advance_chase(delta)\n    if ending or dialog_active:')
s=s.replace('    var nearby := _get_nearby_station()\n    last_near = nearby','''    var paper := _near_evidence()
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
    last_near = nearby''')
s=s.replace('    if current_stage == 2:\n','''    if current_stage == 1 and not valve_solved:
        hud_hint.text = "门禁无电。走廊两侧有阀门；旧记录纸：低压 → 高压 → 低压。"
        progress_bar.visible = false
        return
    if current_stage == 2:
''')
s=s.replace('    if event.is_action_pressed("interact"):\n        if dialog_active:', '''    if event.is_action_pressed("interact"):
        if not dialog_active and not ending and _near_evidence() >= 0:
            _collect_evidence(_near_evidence())
            get_viewport().set_input_as_handled()
            return
        if not dialog_active and not ending and _near_valve() >= 0:
            _turn_valve(_near_valve())
            get_viewport().set_input_as_handled()
            return
        if dialog_active:''')
s=s.replace('elif last_near == current_stage and current_stage != 2 and not ending:', 'elif last_near == current_stage and current_stage != 2 and not ending and (current_stage != 1 or valve_solved):')
s=s.replace('        hud_title.text = CHAPTERS[current_stage]\n        _set_hud_subtitle("门已经打开。你没有被告知原因。")', '        hud_title.text = CHAPTERS[current_stage]\n        if current_stage == 4:\n            _begin_chase()\n        else:\n            _set_hud_subtitle("门已经打开。你没有被告知原因。")')
s=s.replace('        ending = true\n','        ending = true\n        pursuer_active = false\n')
g.write_text(s)
p=root/'game/scripts/player.gd';s=p.read_text()
s=s.replace('@export var move_speed: float = 3.8','@export var move_speed: float = 3.8\n@export var sprint_speed: float = 6.0\n@export var crouch_speed: float = 2.0')
s=s.replace('    velocity.x = direction.x * move_speed\n    velocity.z = direction.z * move_speed', '''    var target_speed := move_speed
    if Input.is_key_pressed(KEY_SHIFT) and not controls_locked:
        target_speed = sprint_speed
    elif Input.is_key_pressed(KEY_CTRL) and not controls_locked:
        target_speed = crouch_speed
    velocity.x = direction.x * target_speed
    velocity.z = direction.z * target_speed''')
p.write_text(s)
print('patched files')
