extends CharacterBody3D

@export var move_speed: float = 3.8
@export var sprint_speed: float = 6.0
@export var crouch_speed: float = 2.0
@export var mouse_sensitivity: float = 0.00165
var camera: Camera3D
var controls_locked: bool = false

func _ready() -> void:
    camera = get_node("Camera3D") as Camera3D

func _unhandled_input(event: InputEvent) -> void:
    if controls_locked:
        return
    if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
        rotate_y(-event.relative.x * mouse_sensitivity)
        camera.rotate_x(-event.relative.y * mouse_sensitivity)
        camera.rotation.x = clamp(camera.rotation.x, -1.28, 1.28)

func _physics_process(delta: float) -> void:
    if not is_on_floor():
        velocity.y -= 18.0 * delta
    else:
        velocity.y = 0.0
    var direction := Vector3.ZERO
    if not controls_locked:
        var axis := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
        direction = (transform.basis * Vector3(axis.x, 0.0, axis.y)).normalized()
    var target_speed := move_speed
    if Input.is_key_pressed(KEY_SHIFT) and not controls_locked:
        target_speed = sprint_speed
    elif Input.is_key_pressed(KEY_CTRL) and not controls_locked:
        target_speed = crouch_speed
    velocity.x = direction.x * target_speed
    velocity.z = direction.z * target_speed
    move_and_slide()
