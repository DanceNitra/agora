; BP_AgoraChar EventGraph, written with BlueprintTools.write_graph_dsl by build_bp_agorachar.
; Third-person control on the project's Enhanced Input actions, read each tick through the
; "Get IA_*" value nodes (the DSL cannot declare Enhanced Input events). Idle/jog switched by speed.

(event EventBeginPlay
  (Variables|Default|SetJogging false)
  (Components|Animation|PlayAnimation :self (Variables|Character|GetMesh) :NewAnimToPlay "/Game/AgoraChar/AF/A_AgoraChar_Idle.A_AgoraChar_Idle" :bLooping true)
  (bind pc (Utilities|Casting|CastToPlayerController :Object (Pawn|GetController))
    (:then
      (bind sub (PlayerController|LocalPlayerSubsystems|GetEnhancedInputLocalPlayerSubsystem :PlayerController pc))
      (Input|AddMappingContext :self sub :MappingContext "/Game/Input/IMC_Default.IMC_Default" :Priority 0)
      (Input|AddMappingContext :self sub :MappingContext "/Game/Input/IMC_MouseLook.IMC_MouseLook" :Priority 0))
    (:CastFailed)))

(event EventTick (DeltaSeconds)
  ; move relative to the camera yaw
  (bind (mx my) (Math|Vector2D|BreakVector2D (Input|EnhancedActionValues|IA_Move)))
  (bind rot (Pawn|GetControlRotation :self (Pawn|GetController)))
  (bind yawRot (Math|Rotator|MakeRotator :Roll 0.0 :Pitch 0.0 :Yaw (.yaw rot)))
  (Pawn|Input|AddMovementInput :WorldDirection (Math|Vector|GetForwardVector :InRot yawRot) :ScaleValue my)
  (Pawn|Input|AddMovementInput :WorldDirection (Math|Vector|GetRightVector :InRot yawRot) :ScaleValue mx)
  ; look: gamepad stick and mouse
  (bind (lx ly) (Math|Vector2D|BreakVector2D (Input|EnhancedActionValues|IA_Look)))
  (bind (ux uy) (Math|Vector2D|BreakVector2D (Input|EnhancedActionValues|IA_MouseLook)))
  (Pawn|Input|AddControllerYawInput :Val (+ lx ux))
  (Pawn|Input|AddControllerPitchInput :Val (+ ly uy))
  ; jump while held
  (if (Input|EnhancedActionValues|IA_Jump)
    (Character|Jump)
    (else
      (Character|StopJumping)))
  ; test switch: walk forward without input
  (if (Variables|Default|GetAutoWalkTest)
    (Pawn|Input|AddMovementInput :WorldDirection (Transformation|GetActorForwardVector) :ScaleValue 1.0))
  ; idle / jog by ground speed
  (bind speed (Math|Vector|VectorLengthXY (Transformation|GetVelocity)))
  (bind moving (> speed 20.0))
  (bind jogging (Variables|Default|GetJogging))
  (if (and moving (not jogging))
    (Variables|Default|SetJogging true)
    (Components|Animation|PlayAnimation :self (Variables|Character|GetMesh) :NewAnimToPlay "/Game/AgoraChar/AF/A_AgoraChar_JogInPlace.A_AgoraChar_JogInPlace" :bLooping true)
    (Components|Animation|SetPlayRate :self (Variables|Character|GetMesh) :Rate 0.78)
    (elif (and (not moving) jogging)
      (Variables|Default|SetJogging false)
      (Components|Animation|PlayAnimation :self (Variables|Character|GetMesh) :NewAnimToPlay "/Game/AgoraChar/AF/A_AgoraChar_Idle.A_AgoraChar_Idle" :bLooping true)
      (Components|Animation|SetPlayRate :self (Variables|Character|GetMesh) :Rate 1.0))))
