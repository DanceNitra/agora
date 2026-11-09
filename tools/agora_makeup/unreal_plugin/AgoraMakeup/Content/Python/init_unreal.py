# Agora Makeup: adds Tools > Agora Makeup to the editor menu.
try:
    import agora_makeup_ue.menu
    agora_makeup_ue.menu.register()
except Exception as e:  # never block editor start
    import unreal
    unreal.log_warning("Agora Makeup menu not registered: %s" % e)
