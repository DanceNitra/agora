; BP_AgoraChar EventGraph, written with BlueprintTools.write_graph_dsl by build_bp_agorachar.
; Third-person control on the project's Enhanced Input actions, read each tick through the
; "Get IA_*" value nodes (the DSL cannot declare Enhanced Input events). Animation comes from ABP_Unarmed_Agora (Epic ABP_Unarmed retargeted).

(event EventBeginPlay
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
  (if (or (Input|EnhancedActionValues|IA_Jump) (Variables|Default|GetJumpTest))
    (Character|Jump)
    (else
      (Character|StopJumping)))
  ; test switch: walk forward without input
  (if (Variables|Default|GetAutoWalkTest)
    (Pawn|Input|AddMovementInput :WorldDirection (Transformation|GetActorForwardVector) :ScaleValue 1.0)))
