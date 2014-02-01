


def junction_reply(area, areas, replies):
    total_area = area + sum(areas)
    
    return area / (total_area*(0.5 - sum( a/(total_area*(1.0/r+1.0)) for a,r in zip(areas, replies) ))) - 1.0
    
    #Equivalently?
    #x = area / (total_area*(0.5 - sum( a/(total_area*(r+1.0)) for a,r in zip(areas, replies) ))) - 1.0
    #return 1/x


def junction2_reply(area, area1, reply1):
    total_area = area + area1
    
    return area / (total_area*(0.5 - area1/(total_area*(1.0/reply1+1.0)))) - 1.0


def junction3_reply(area, area1, area2, reply1, reply2):
    total_area = area + area1 + area2
    
    return area / (total_area*(
        0.5 
        - area1/(total_area*(1.0/reply1+1.0))
        - area2/(total_area*(1.0/reply2+1.0))
    )) - 1.0




def new2(a1, r1):
    #pjunc = 2.0*(reply1+1.0)/(reply1+1.0-area1*reply1)
    
    #pout1 = 2.0 / (r1+1.0-a1*r1-a1)
    #pout1 = -2.0 / (-r1-1.0+a1*r1-a1)
    pout1 = 2.0/(r1+1.0-a1*r1+a1)
    pjunc = pout1 + r1*pout1

    
    pin1 = r1 * pout1
    pin0 = 1.0
    pout0 = pjunc - pin0
    print
    print pout1 + pin1    
    print pjunc
    print
    print pin0-pout0+a1*(pin1-pout1)
    print
    
    return pjunc - 1.0


def new3(a1, a2, r1, r2):
    pjunc = 2.0 / (1.0-a1*(r1-1.0)/(r1+1.0)-a2*(r2-1.0)/(r2+1.0))
    
    pout1 = pjunc / (r1+1.0)
    pout2 = pjunc / (r2+1.0)
    print abs(pout1)
    print abs(pout2)

    return pjunc - 1.0


area = 1.0
area1 = 5.0
reply1 = -1j
area2 = 4.0
reply2 = 1

#print junction2_reply(area, area1, reply1)
#print new2(area1, reply1)

print junction3_reply(area,area1,area2, reply1,reply2)
print new3(area1, area2, reply1, reply2)


