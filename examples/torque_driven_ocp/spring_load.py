"""
This trivial spring example targets to have the highest upward velocity. It is however only able to load a spring by
pulling downward and afterward to let it go so it gains velocity. It is designed to show how one can use the external
forces to interact with the body.
"""

from casadi import MX
import biorbd
from bioptim import (
    OptimalControlProgram,
    Dynamics,
    Problem,
    Objective,
    DynamicsFunctions,
    ObjectiveFcn,
    Bounds,
    QAndQDotBounds,
    InitialGuess,
    ShowResult,
    NonLinearProgram,
)


def custom_dynamic(states: MX, controls: MX, parameters: MX, nlp: NonLinearProgram) -> tuple:
    """
    The dynamics of the system using an external force (see custom_dynamics for more explanation)

    Parameters
    ----------
    states: MX
        The current states of the system
    controls: MX
        The current controls of the system
    parameters: MX
        The current parameters of the system
    nlp: NonLinearProgram
        A reference to the phase of the ocp

    Returns
    -------
    The state derivative
    """

    q, qdot, tau = DynamicsFunctions.dispatch_q_qdot_tau_data(states, controls, nlp)

    force_vector = MX.zeros(6)
    force_vector[5] = 100 * q[0] ** 2

    f_ext = biorbd.VecBiorbdSpatialVector()
    f_ext.append(biorbd.SpatialVector(force_vector))
    qddot = nlp.model.ForwardDynamics(q, qdot, tau, f_ext).to_mx()

    return qdot, qddot


def custom_configure(ocp: OptimalControlProgram, nlp: NonLinearProgram):
    """
    The configuration of the dynamics (see custom_dynamics for more explanation)

    Parameters
    ----------
    ocp: OptimalControlProgram
        A reference to the ocp
    nlp: NonLinearProgram
        A reference to the phase of the ocp
    """
    Problem.configure_q_qdot(nlp, as_states=True, as_controls=False)
    Problem.configure_tau(nlp, as_states=False, as_controls=True)
    Problem.configure_dynamics_function(ocp, nlp, custom_dynamic)


# Model path
m = biorbd.Model("mass_point.bioMod")
m.setGravity(biorbd.Vector3d(0, 0, 0))

# Add objective functions (high upward velocity at end point)
objective_functions = Objective(ObjectiveFcn.Mayer.MINIMIZE_STATE, index=1, weight=-1)

# Dynamics
dynamics = Dynamics(custom_configure, dynamic_function=custom_dynamic)

# Path constraint
x_bounds = QAndQDotBounds(m)
x_bounds[:, 0] = [0] * m.nbQ() + [0] * m.nbQdot()
x_bounds.min[:, 1] = [-1] * m.nbQ() + [-100] * m.nbQdot()
x_bounds.max[:, 1] = [1] * m.nbQ() + [100] * m.nbQdot()
x_bounds.min[:, 2] = [-1] * m.nbQ() + [-100] * m.nbQdot()
x_bounds.max[:, 2] = [1] * m.nbQ() + [100] * m.nbQdot()

# Initial guess
x_init = InitialGuess([0] * (m.nbQ() + m.nbQdot()))

# Define control path constraint
u_bounds = Bounds([-100] * m.nbGeneralizedTorque(), [0] * m.nbGeneralizedTorque())

u_init = InitialGuess([0] * m.nbGeneralizedTorque())
ocp = OptimalControlProgram(
    m,
    dynamics,
    n_shooting=30,
    phase_time=0.5,
    x_init=x_init,
    u_init=u_init,
    x_bounds=x_bounds,
    u_bounds=u_bounds,
    objective_functions=objective_functions,
)

# --- Solve the program --- #
sol = ocp.solve(show_online_optim=True)

# --- Show results --- #
result = ShowResult(ocp, sol)
result.animate()
