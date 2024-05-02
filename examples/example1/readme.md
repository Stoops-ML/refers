# Example 1
This document demonstrates the `refers` library in action.

Run `refers -r example1` in command prompt to output the file [readme_refers.md](readme_refers.md), which will convert the references using the requested tags.

## Demonstration
The file [@ref:dist_eq:file](@ref:dist_eq:link) is a script that simulates linear motion.

On line @ref:dist_eq:line the distance equation is written as follows: $d = vt + \frac{1}{2}at^2$. 

A better method for numerical integration is the Runge-Kutta fourth-order method. 
Lines @ref:k1:line through @ref:k4:line show the four tangent calculations, which are combined in a weighted average:
`@ref:weight_ave:quotecode`
