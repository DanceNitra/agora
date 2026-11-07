; BP_AgoraMH BeginPlay: the MetaHuman outfit follows the body's pose (leader pose), then the input mapping
; contexts are added exactly as in BP_AgoraChar.dsl. Face and grooms follow through MetaHumanComponent.
(event EventBeginPlay
  (Components|SkinnedMesh|SetLeaderPoseComponent :self (Variables|Default|GetOutfit) :NewLeaderBoneComponent (Variables|Character|GetMesh))
  (bind pc (Utilities|Casting|CastToPlayerController :Object (Pawn|GetController))
    (:then
      (bind sub (PlayerController|LocalPlayerSubsystems|GetEnhancedInputLocalPlayerSubsystem :PlayerController pc))
      (Input|AddMappingContext :self sub :MappingContext "/Game/Input/IMC_Default.IMC_Default" :Priority 0)
      (Input|AddMappingContext :self sub :MappingContext "/Game/Input/IMC_MouseLook.IMC_MouseLook" :Priority 0))
    (:CastFailed)))
