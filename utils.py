
def is_admin(member):
    return member.server_permissions.administrator or member.id == "199218932496859137"
    
def shortened(cont, charlim=64):
    if len(cont) > charlim or len(cont.split("\n"))>1: 
        cont = cont.split("\n")[0][:charlim] + "..."
    return cont
