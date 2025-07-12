
import sys, math, random, bisect, multiprocessing, signal, time

from . import legion, grace

#def status(*items):
#    """ Display a status string. """
#    string = ' '.join( str(item) for item in items )
#    if sys.stderr.isatty():
#        sys.stderr.write('\r  \x1b[K\x1b[34m' + string + '\x1b[m\r')
#        sys.stderr.flush()


def worker(scorer, fut):
    while True:
        value = legion.coordinator().get_future(fut)
        if value is None: 
            break
        
        item, reply_fut = value
        result = scorer(item)        
        fut = legion.coordinator().new_future()
        legion.coordinator().deliver_future(reply_fut, (result, fut))


def make_update(vecs, initial_accuracy, do_noise):
    do_noise = do_noise or random.random() < 0.1

    #vecs = random.sample(vecs,min(100,len(vecs)))
    
    n = len(vecs)
    m = len(vecs[0])
    
    #mean = [ 
    #    sum([ vec[i] for vec in vecs ])/n 
    #    for i in xrange(m) 
    #    ]

    #weight_weight = (1.25+random.random()) / (n**0.5)
    weight_weight = (1.0+2.0*random.random()) / (n**0.5)
    #weight_weight = (1.0) / (n**0.5)
    weights = [ 
        random.normalvariate(0.0, weight_weight) 
        for i in range(n) 
        ]
    
    offset = (0.0-sum(weights)) / n
    weights = [ weight+offset for weight in weights ]
    weights[ random.randrange(n) ] += 1.0
    
    update = [ 
        sum( vecs[j][i]*weights[j] for j in range(n) )
        for i in range(m) 
        ]
    
    #update = [ 
    #    sum( 
    #        (vecs[j][i]-mean[i])*weights[j] 
    #        for j in xrange(n) 
    #        ) + mean[i]
    #    for i in xrange(m) 
    #    ]

    if do_noise:
        extra = random.random() * initial_accuracy
        update = [ 
            val+random.normalvariate(0.0, extra) 
            for val in update 
            ]

    return update


def show_status(line):
    print("\r\033[K\r" + line, end="")
    sys.stdout.flush()

def improve(comment, constrainer, scorer, start_x, ftol=1e-4, xtol=1e-6, initial_accuracy=0.001, pool_factor=5, workers=1, monitor = lambda x,y: None):
    serial = (workers <= 1)
    if not serial:
        worker_futs = [ legion.coordinator().new_future() for i in range(workers) ]
        reply_futs = [ ]
        
        workers = [
            legion.future(worker,scorer,fut)
            for fut in worker_futs 
            ]
    
    last_t = 0.0
    best = start_x
    c_score = constrainer(best)
    if c_score:
        best_score = (c_score, 0.0)
    else:
        best_score = (0.0, scorer(best))
    
    n = 0
    n_good = 0
    n_real = 0
    n_real_since_best = 0  # A way to at some point give up
    jobs = [ ]
    
    pool_size = int(len(best)*pool_factor) #5
    print(len(best),'parameters, pool size', pool_size)

    currents = [ (best, best_score) ]
    
    done = False
    while not done or (not serial and reply_futs):
        t = time.time()
        if t > last_t+20.0:
            def rep(x): 
                if x[0]: return 'C%.6f' % x[0]
                return '%.6f' % x[1]
            status = f"Optimizing {comment} best={rep(best_score)} worst={rep(max(item[1] for item in currents))} pool={len(currents)} n_good={n_good} n_real={n_real} n={n}"
            show_status(status)
            
            if best_score[0] == 0:
                monitor(best, [ item[0] for item in currents ])
            last_t = time.time()
        
        have_score = False
        
        if not done and (serial or worker_futs):
            new = make_update([item[0] for item in currents], initial_accuracy, len(currents) < pool_size)
            
            c_score = constrainer(new)
            if c_score:
                have_score = True
                new_score = (c_score, 0.0)
            elif workers == 1:
                have_score = True
                new_score = (0.0, scorer(new))
            else:
                reply_fut = legion.coordinator().new_future()
                worker_fut = worker_futs.pop(0)                    
                legion.coordinator().deliver_future(worker_fut, (new, reply_fut))
                reply_futs.append( (new, reply_fut) )
        
        if not have_score:
            if not reply_futs or (not done and worker_futs):
                continue
            new, reply_fut = reply_futs.pop(0)
            new_score, worker_fut = legion.coordinator().get_future(reply_fut)
            new_score = (0.0, new_score)
            worker_futs.append(worker_fut)
        
        n += 1
        if new_score[0] == 0.0:
            n_real += 1
            n_real_since_best += 1

        l = sorted( item[1][1] for item in currents )
        if pool_size < len(l):
            c = l[pool_size]
        else:
            c = 1e30
        cutoff = (best_score[0], c)
        
        if new_score <= cutoff:
            currents = [ item for item in currents if item[1] <= cutoff ]
            currents.append((new,new_score))
            
            n_good += 1
        
            if new_score < best_score:
                best_score = new_score
                best = new
                n_real_since_best = 0
        
        if len(currents) >= pool_size and best_score[0] == 0.0:
            xspan = 0.0
            for i in range(len(start_x)):
                xspan = max(xspan,
                    max(item[0][i] for item in currents) -
                        min(item[0][i] for item in currents)
                    )
            
            fspan = (max(item[1] for item in currents)[1]-best_score[1]) 
            
            if xspan < xtol or (n_good >= 5000 and fspan < ftol):
                done = True
        
        # Give up if completely stuck
        if n_real_since_best >= 1000000:
            show_status('')
            print("No improvement in 1,000,000 tries.")
            done = True
    
    show_status('')
    print(f"Optimized {comment} best={best_score[1]:.5f}")
        
    if not serial:
        while worker_futs:
            fut = worker_futs.pop(0)
            legion.coordinator().deliver_future(fut, None)
        
        for item in workers:
            item()
    
    return best
        
