# Example 1
This document demonstrates the `refers` library in action.

Run `refers -r example1` in command prompt to output the file [readme_refers.md](readme_refers.md), which will convert the referenced tag using the option.

## Demonstration
The file [suvat.py](src/suvat.py) is a script that simulates linear motion.

On line 14 the distance equation is written as follows: $d = vt + \frac{1}{2}at^2$. 

A better method for numerical integration is the Runge-Kutta fourth-order method. 
Lines 22 through 25 show the four tangent calculations, which are combined in a weighted average:
`X += dt * (k1 + 2 * k2 + 2 * k3 + k4) / 6`
