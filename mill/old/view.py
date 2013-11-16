
import sys, pylab

f = open('r.dump','rb')
item = eval(f.read().strip())
f.close()

xs = [ ]
ys = [ ]
zs = [ ]
for item2 in item:
    xs.append(item2[0][0])
    ys.append(item2[0][1])
    zs.append(item2[0][2])

if 't' in sys.argv[1:]:
    pylab.subplot(3,1,1)
    pylab.plot(xs)
    pylab.subplot(3,1,2)
    pylab.plot(ys)
    pylab.subplot(3,1,3)
    pylab.plot(zs)
    pylab.show()

else:
    
    import matplotlib as mpl
    from mpl_toolkits.mplot3d import Axes3D
    import numpy as np
    import matplotlib.pyplot as plt
    
    mpl.rcParams['legend.fontsize'] = 10
    
    fig = plt.figure()
    ax = fig.gca(projection='3d')
    #theta = np.linspace(-4 * np.pi, 4 * np.pi, 100)
    #z = np.linspace(-2, 2, 100)
    #r = z**2 + 1
    #x = r * np.sin(theta)
    #y = r * np.cos(theta)
    #ax.plot(xs, ys, zs, ',')
    
    n = 20
    for i in xrange(n-1,-1,-1):
        a = i*(len(xs)-1)//n
        b = (i+1)*(len(xs)-1)//n + 1
        c = 1.0*i/n
        c2 = abs(c*2-1)
        ax.plot(xs[a:b], ys[a:b], zs[a:b], color=(c,c2,1-c))
    
    ax.legend()
    
    plt.show()
    
