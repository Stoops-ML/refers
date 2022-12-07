# Example 1
This document demonstrates the `refers` library. 
Run the `refers` library in command prompt to achieve the same results here.

## Demostration
The file [suvat.py](src/suvat.py) is a script that simulates linear motion.

On line 14 the distance equation is written as follows: $d = vt + \frac{1}{2}at^2$. 

A better method for numerical integration is the Runge-Kutta fourth-order method. 
Lines 22 through 25 show the four tangent calculations, which are combined in a weighted average:
`X += dt * (k1 + 2 * k2 + 2 * k3 + k4) / 6`