import numpy as np


# simple SUVAT simulation
if __name__ == "__main__":
    # parameters
    speed = 10  # m/s
    acceleration = 2  # m/s^2
    time = np.arange(100)  # s
    time_step = np.diff(time)  # s
    distance0 = 0  # m

    # simulation: SUVAT
    distance = distance0 + speed * time + 0.5 * acceleration * time**2  # @tag:dist_eq

    # simulation: Runge-Kutta 4
    def solve_ODE(t, X):  # @tag:solve_ode
        return np.array([X[1], acceleration])

    X = np.array([distance0, speed], dtype=np.float32)
    for t, dt in zip(time, time_step):
        k1 = solve_ODE(t, X)  # @tag:k1
        k2 = solve_ODE(t + dt / 2, X + dt / 2 * k1)
        k3 = solve_ODE(t + dt / 2, X + dt / 2 * k2)
        k4 = solve_ODE(t + dt, X + dt * k3)  # @tag:k4
        X += dt * (k1 + 2 * k2 + 2 * k3 + k4) / 6  # @tag:weight_ave
