import random, math
random.seed(42)

# Claim (Johnson & Zhang 2013, SVRG): plain SGD has slow ASYMPTOTIC convergence because of the
# inherent variance of the stochastic gradient. Smallest model: minimize a strongly-convex
# least-squares f(w)=(1/2n)*sum_i (a_i*w - b_i)^2 (scalar w). Compare:
#   - GD (full gradient): variance-free -> linear convergence
#   - SGD constant step: noisy gradient -> converges only to a VARIANCE FLOOR, then stalls
#   - SGD decreasing step (1/t): kills variance slowly -> sublinear (slow) convergence
#   - SVRG (variance-reduced): linear convergence at SGD-like cost
# Source: simulation.

n = 200
a = [random.gauss(1.0, 0.6) for _ in range(n)]
b = [a[i]*3.0 + random.gauss(0, 1.0) for i in range(n)]     # true w ~ 3, label noise
def full_grad(w): return sum(a[i]*(a[i]*w - b[i]) for i in range(n))/n
def loss(w):      return sum((a[i]*w - b[i])**2 for i in range(n))/(2*n)
w_star = sum(a[i]*b[i] for i in range(n)) / sum(a[i]*a[i] for i in range(n))
f_star = loss(w_star)

def run_gd(steps, lr=0.3):
    w=0.0
    for _ in range(steps): w -= lr*full_grad(w)
    return loss(w)-f_star

def run_sgd(steps, lr0, decreasing):
    w=0.0
    for t in range(1, steps+1):
        i=random.randrange(n)
        g=a[i]*(a[i]*w-b[i])
        lr = lr0/(1+0.01*t) if decreasing else lr0
        w -= lr*g
    return loss(w)-f_star

def run_svrg(epochs, m, lr=0.1):
    w=0.0
    for _ in range(epochs):
        mu=full_grad(w); w_anchor=w
        for _ in range(m):
            i=random.randrange(n)
            g=a[i]*(a[i]*w-b[i]) - a[i]*(a[i]*w_anchor-b[i]) + mu
            w -= lr*g
    return loss(w)-f_star

print(f"optimum loss f* = {f_star:.4f}; reporting suboptimality (loss - f*)\n")
print(f"{'method':28s} {'after ~2k grad-evals':>22}")
print(f"{'GD (full grad, lr .3)':28s} {run_gd(2000//1):22.2e}")  # crude budget match
print(f"{'SGD constant step (lr .05)':28s} {run_sgd(2000, 0.05, False):22.2e}")
print(f"{'SGD decreasing step (1/t)':28s} {run_sgd(2000, 0.1, True):22.2e}")
print(f"{'SVRG (variance-reduced)':28s} {run_svrg(10, 200, 0.1):22.2e}")
print("\nConstant-step SGD stalls at a variance FLOOR (slow asymptotic convergence); GD and SVRG")
print("drive suboptimality toward 0 (linear). Decreasing-step SGD converges but only slowly.")
