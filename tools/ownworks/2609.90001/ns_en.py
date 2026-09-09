# -*- coding: utf-8 -*-
"""2609.90001 «Finite Time Blowup for Navier–Stokes» (OpenAI, 8 Sep 2026). English.

Written by hand, no model. Retelling in our own words (licence class analysis).
"""

FORMULAS_ADV = [
    {"description": "Navier–Stokes with an external force: Newton's law for a fluid parcel",
     "latex": r"\partial_t u + (u\cdot\nabla)u - \nu\Delta u + \nabla p = f,\qquad \nabla\cdot u = 0",
     "meaning": "The parcel's acceleration (left) equals the sum of forces: pressure, viscous friction and the external force f. The second equation is incompressibility. In the paper f is smooth and compactly supported, while u and p are constructed so that the equation holds identically."},
    {"description": "The residual: defining the force from a chosen flow",
     "latex": r"R(u,p) = \partial_t u + (u\cdot\nabla)u - \Delta u + \nabla p",
     "meaning": "The central move. Velocity and pressure are written down by hand and the force is declared to be the residual R. The equation then holds by construction; the whole task is to make R and all its derivatives smooth as t → 1 while u → ∞."},
    {"description": "Scales of the collapsing core (τ = 1 − t, time left to blowup)",
     "latex": r"\ell_r \asymp \tau^{1/2},\qquad \ell_z \asymp \tau^{1/2-h},\qquad 0<h<\tfrac{1}{100}",
     "meaning": "The radius shrinks faster than the height: ℓ_r/ℓ_z ≍ τ^h → 0. The core stretches into a thin needle of volume ~τ^{3/2−h}."},
    {"description": "Velocities and energy of the core",
     "latex": r"|u_\theta|,\,|u_z| \asymp \tau^{-1/2-h},\qquad E_{\text{core}} \asymp \tau^{1/2-3h} \to 0",
     "meaning": "Speed diverges while the core's kinetic energy tends to zero: the volume falls faster than the square of the speed grows. Infinite speed lives in an ever thinner needle."},
    {"description": "Two Reynolds numbers of the core",
     "latex": r"\mathrm{Re}_\theta = \frac{|u_\theta|\,\ell_r}{\nu} \asymp \tau^{-h}\to\infty,\qquad \mathrm{Re}_r = \frac{|u_r|\,\ell_r}{\nu} = O(1)",
     "meaning": "Rotation outruns viscosity (Re_θ grows) while radial inflow keeps pace with it (Re_r bounded). Viscosity is not defeated; it is built into the leading balance and stays there up to the blowup."},
    {"description": "Spin-up under contraction: conservation of angular momentum",
     "latex": r"r\,u_\theta = \text{const}\ \Rightarrow\ u_\theta \propto \frac{1}{r}",
     "meaning": "A parcel with no torque rotates faster as it approaches the axis, like a skater pulling in her arms. In the real core viscosity carries some angular momentum away; the balance of inward transport against viscous loss sets the growth of speed."},
    {"description": "Mean momentum flux from a zero-mean oscillation",
     "latex": r"\langle u'_r\,u'_\theta\rangle \neq 0\quad\text{while}\quad \langle u'_r\rangle=\langle u'_\theta\rangle=0",
     "meaning": "Reynolds stress: if outward-moving fluid carries a surplus of rotation and inward-moving fluid a deficit, the product keeps its sign in both half-cycles. Pulses with no mean velocity thus deliver a mean force, and that force plugs the hole in the background balance."},
]

KEY_NUMBERS_ADV = {
    "viscosity ν": "any ν > 0",
    "blowup time": "t = 1, start from rest u(·,0) = 0",
    "core radius": "~ τ^{1/2}, τ = 1 − t",
    "core height": "~ τ^{1/2−h}, h < 1/100",
    "core speed": "~ τ^{−1/2−h} → ∞",
    "core energy": "~ τ^{1/2−3h} → 0",
    "rotational Reynolds number": "~ τ^{−h} → ∞",
    "size of the work": "166 pages + Lean formalization",
    "agents in the group": "≈ 10,000, 88 hours",
    "Lean check": "17 hours; 2.7 M messages, ≈130 B output tokens",
}

ABSTRACT = {
    "popular": "OpenAI has shown that a three-dimensional fluid governed by the Navier–Stokes equations can reach infinite speed in finite time. The flow starts from complete rest, is driven by a smooth external force bounded in space and time, and its energy stays finite. The blowup is a needle-like vortex: fluid spirals toward the axis and escapes along it, the core shrinks and speeds up, and small oscillations in the ring around the core themselves produce the force the background was missing. This settles alternatives (C) and (D) of the official Millennium Prize statement; (A) and (B), the unforced case, remain open. The proof was found by about 10,000 AI agents in 88 hours and formalized in Lean.",
    "simple": "AI agents at OpenAI built a whirlpool that reaches infinite speed in finite time even though its energy keeps shrinking. The fluid starts at rest, a smooth external force pushes it, and the water spirals toward the axis and flows out along it like a thin needle. Viscosity does not stop it, because it was built into the balance, and the missing force is produced by the fluid itself through small oscillations around the core. This answers part of the famous Millennium Prize problem, but not all of it: the version without an external force is still open.",
    "advanced": "For every ν > 0 the authors construct a force f ∈ C_c^∞(R³×(0,∞)), a compact set K and smooth u, p on R³×[0,1) solving Navier–Stokes with u(·,0) = 0, supp u(·,t) ∪ supp p(·,t) ⊂ K, sup_t‖u(t)‖_{L²} < ∞ and limsup_{t↑1}‖u(t)‖_{L^∞} = ∞. Consequently no smooth solution with uniformly bounded energy exists on R³×[0,∞) for the same force and data, which gives alternative (C) of Fefferman's statement and, by compactness, alternative (D) on the torus. The construction: a self-similar axisymmetric vortex with ℓ_r ≍ τ^{1/2}, ℓ_z ≍ τ^{1/2−h}, speeds ≍ τ^{−1/2−h} and core energy ≍ τ^{1/2−3h} → 0; the background residual in the matching annulus is unbounded and is cancelled by the mean quadratic fluxes of oscillatory pulses of two families that grow on the background shear and are damped by viscosity as their radial wavelength shortens; the exterior flow solves the radial heat equation exactly and needs no force. The proof was produced by a system of AI agents and formalized in Lean.",
}

THREADS = "For ninety years the Navier–Stokes equations gave no answer: can a smooth fluid accelerate to infinity? Here the answer is built by hand, or rather by machines: the flow is written down and the force is declared to be the residual. The blowup lives in a needle that shrinks faster than it speeds up, so energy falls while speed grows. And the most beautiful part: the missing force is produced by the fluid itself, through small oscillations that flare up and die out on their own."

SIMPLE = {
    "title": "How water can accelerate to infinity, and why machines proved it",
    "oneliner": "AI agents built a whirlpool that reaches infinite speed in finite time while its energy keeps shrinking. A step-by-step explanation of how it works.",
    "description": "The Navier–Stokes equations describe how water, air and blood flow. For ninety years nobody knew whether a smooth flow could break down and produce infinite speed under these equations. In September 2026 a system of AI agents at OpenAI built such a flow and proved it in 166 pages and in Lean, a language of formally checked proofs. Here is, in plain words, how it works and what exactly was proved.",
    "text": """Picture a bathtub. Water flows, swirls, slows down through friction. The rules it follows fit in two lines, the Navier–Stokes equations: Newton's law, force equals mass times acceleration, for every drop, plus the condition that water cannot be compressed. These equations are used to design aircraft, forecast weather and model blood in vessels.

Here is the question nobody could close for ninety years. If the water flows smoothly at the start, can it, under these equations, ever accelerate to infinite speed? Real water never does, but the equations are a model. If speed becomes infinite in the model, the model breaks at that moment. Mathematicians call such a moment a singularity, and the question itself is a Millennium Prize problem, with a million dollars attached.

Now there is an answer, though not to the whole question. Let us go step by step.

**The trick that started it all.** Usually you solve forward: take the water, run the equations, see what happens. Ninety years of that led nowhere. Here they did the opposite. The equation can be read as a definition of the force: write down any flow, plug it into the equation, and call whatever does not balance the external force. The equation then holds automatically. Inventing a flow that accelerates to infinity is easy. The hard part is different: the force must stay smooth, calm, with no infinities. That is the entire work.

**The needle whirlpool.** The flow is built around a vertical axis, like water above a drain. Water spirals toward the axis and at the same time flows out along the axis, up and down. Why does it speed up? Because rotation is conserved: the closer to the axis, the faster the turn, like a skater pulling in her arms. And why does it not clog the axis and stop? Because water cannot be compressed, so the inflowing water is carried away along the axis. The inflow can continue indefinitely.

Now the surprising part. The core of the whirlpool shrinks: a fraction of a second before the blowup its radius is already tiny. But it shrinks unevenly. The radius decreases faster than the height, and the core stretches into a thin needle. And here is what happens: the speed in the needle goes to infinity while the energy of the whole needle goes to zero. No miracle: energy is speed squared times volume, and the volume of the needle falls faster than the square of the speed grows. Infinite speed lives in an ever thinner thread.

**Why friction does not save the day.** Viscosity, the friction inside water, smooths everything sharp. That is why many believed blowup impossible. This work does not fight friction. It builds it into the balance. In rotation the whirlpool outruns friction: the closer to the blowup, the more turns the water makes while friction slows it. In the inflow toward the axis friction stays an equal partner. Everything accelerates together and at the same rate, to the very end.

**The place where it almost broke.** The core is honest on its own. But it has to join the calm water outside. In the ring between the core and the outer water the equations do not balance, and the force needed there grows to infinity. That is a failure: the force is not allowed to be infinite.

**The fluid supplies its own force.** This is the main idea. Into the ring around the core they plant small oscillations, each a full ring around the axis, started by a tiny push. An oscillation has zero average velocity: the water jiggles back and forth. But imagine this: when it moves outward it carries a surplus of rotation, and when it moves inward, a deficit. The product of "where it goes" and "what it carries" has the same sign in both cases. So an oscillation with zero mean velocity transports rotation steadily in one direction. That transport acts on the water like a real force, and it was tuned to plug the hole in the ring exactly.

**Where the oscillations get their energy and why they do not grow forever.** They feed on the whirlpool itself: a drop with a surplus of rotation is pushed outward, where its surplus becomes more pronounced, and so on, as long as amplification beats friction. And they die on their own. The whirlpool turns different layers at different speeds and gradually makes the oscillation pattern finer. Friction eats fine patterns quickly. The initial size was chosen so that the oscillation grows first and then inevitably dies, leaving almost nothing behind. Each flares up and fades by itself.

**Assembly.** There are two families of oscillations, because two holes must be plugged: the transport of rotation and the transport of motion along the axis. Closer to the blowup they are placed ever finer and ever more often. Outside the ring the water simply circles the axis and slows down through friction exactly as the heat equation dictates, so no force is needed there at all. And the whole thing can be cut off neatly in space: the flow occupies a bounded volume, and the force acts for a bounded time.

**What was proved and what was not.** Proved: for any viscosity there is a smooth, bounded force under which water that was at rest reaches infinite speed in finite time while its energy stays finite. The official Millennium statement lists four alternatives: (A) and (B), smoothness always holds without an external force, and (C) and (D), breakdown happens with a smooth force. This work settles (C) and (D). The author of the statement wrote explicitly that a proof of any of the four counts, and OpenAI says it will not claim the prize. But the unforced question, the one people usually mean, stays open. And keep in mind: since the water was at rest, all the energy was put in by the external force. There is no "order out of nothing" here, only a very precise calculation of how to push.

**Who did it.** The proof was found by a group of roughly ten thousand AI agents in 88 hours of work; another 17 hours went into checking it in Lean, where a computer verifies every step. A week earlier, mathematicians Tristan Buckmaster and Levent Alpöge used the same forcing trick to prove a similar result for the Euler equations, where there is no friction. A priority dispute followed, but the mathematics in both works stands on its own. This may be what part of science now looks like: the tools are old and well known, and carrying the construction to the end is long, done by machine and checked by machine.""",
    "fun_fact": "The speed in the needle goes to infinity while its energy goes to zero: the volume shrinks faster than the square of the speed grows. Infinite speed with vanishing energy, and not a single law of physics is broken.",
    "scifi": "",
    "formulas": [
        {"description": "Spin-up under contraction: rotation is conserved",
         "latex": r"r\,u_\theta = \text{const}",
         "meaning": "The closer a drop is to the axis (smaller r), the faster it rotates (larger u_θ). This is how a skater speeds up by pulling in her arms."},
        {"description": "The core's energy vanishes although its speed grows",
         "latex": r"E \sim u^2 \cdot V,\qquad u\to\infty,\ V\to 0,\ E\to 0",
         "meaning": "Energy is speed squared times volume. The needle's volume falls faster than the square of the speed grows, so the energy tends to zero."},
    ],
}

POPULAR = {
    "title": "A needle of water: how 10,000 agents made the Navier–Stokes equations blow up",
    "oneliner": "From rest, with a smooth force and finite energy: a flow whose speed goes to infinity in finite time. How it was built and what it means for the Millennium Prize problem.",
    "description": "On 8 September 2026 OpenAI released a 166-page paper and its Lean formalization: a three-dimensional incompressible fluid governed by the Navier–Stokes equations can reach infinite speed in finite time. The flow starts from rest, is driven by a smooth force bounded in space and time, and its energy stays finite. This settles two of the four alternatives in the official statement of the Millennium Prize problem. The proof was assembled by a group of about ten thousand AI agents in 88 hours.",
    "threads": THREADS,
    "text": """In 1934 Jean Leray proved that the Navier–Stokes equations always have solutions "in a generalized sense". Whether a solution stays smooth or can break down into a singularity he could not tell, and nobody could for ninety years. In 2000 the Clay Institute made the question one of its seven Millennium Prize problems. The statement written by Charles Fefferman is honest: he asks for a proof of any one of four claims. (A) and (B): without an external force smoothness always holds, in space and on the torus. (C) and (D): there exist a smooth force and smooth initial data for which no smooth finite-energy solution exists.

OpenAI's paper proves (C) and (D). For every viscosity ν > 0 it constructs a smooth force, compactly supported in space and time, and a flow that starts from complete rest, keeps its energy bounded and reaches infinite speed at t = 1. How this is done is worth understanding, because the method turns the problem inside out.

**The problem is solved backwards.** The Navier–Stokes equation can be read as a definition of the force. Write down any velocity u and pressure p, substitute them, and declare whatever fails to balance to be the external force f. The equation holds identically. A blowing-up flow is easy to invent. The difficulty moves to one place: the residual must be smooth. Individual terms in it diverge, and one has to arrange cancellations so that the sum and all its derivatives pass calmly through the blowup time. That is what the 166 pages are spent on.

**The needle vortex.** A vortex on the vertical axis collapses toward the origin. Inside, fluid spirals toward the axis and flows out along it, up and down. Conservation of angular momentum drives the spin-up: for a parcel with no torque r·u_θ is constant, so smaller r means larger u_θ. Incompressibility keeps the inflow going: the incoming fluid is carried away by the axial flow, otherwise it would clog the axis.

The core contracts self-similarly: the profile keeps its shape and only the scales change. Let τ = 1 − t be the time left to blowup. The core radius is ~τ^{1/2}, the height ~τ^{1/2−h} with a tiny h < 1/100, the speeds ~τ^{−1/2−h}. The radius shrinks faster than the height, so the core stretches into a thin needle of volume ~τ^{3/2−h}. From here comes the most elegant point of the paper: the core's kinetic energy ~τ^{1/2−3h} tends to zero. The speed is infinite, the energy vanishes, the volume falls faster than the square of the speed grows.

**Viscosity is not defeated but built in.** Viscosity is what separates Navier–Stokes from Euler, and it is why the equation was thought perhaps to be safe. The paper computes two Reynolds numbers. In rotation Re_θ ~ τ^{−h} → ∞: the fluid makes ever more turns within a viscous diffusion time, rotation wins. In the radial inflow Re_r = O(1): viscosity remains an equal partner. The rates of all processes, axial and radial transport and diffusion across the core, grow alike as τ^{−1} and stay in the leading balance to the end. Along the axis diffusion is weaker by a factor τ^{2h}, and the construction uses that gap.

**Where it breaks.** The core has to be stitched to calm fluid outside. In the annulus between core and exterior the stitching does not balance, and the residual grows without bound as t → 1. The force must be smooth, yet here it would have to be infinite. The background vortex does not sustain itself.

**The fluid produces the force itself.** Into the annulus they plant small oscillating disturbances, each a complete ring around the axis, localized in radius, height and time and started by an exponentially small seed. How does a zero-mean oscillation yield a nonzero force? Moving outward, fluid carries a surplus of azimuthal velocity; moving inward, a deficit. The mean velocity is zero, but the flux of angular momentum, the product of the two, keeps its sign in both half-cycles. Flip both signs and the product is unchanged. The result is a steady mean momentum flux whose spatial variation acts on the background like a genuine force. Physicists call this Reynolds stress and usually treat it as a nuisance; here it is a tool, tuned to cancel exactly the divergent part of the residual.

**The pulses flare and fade on their own.** They grow on the background shear by a centrifugal mechanism: a parcel with surplus rotation is pushed outward, and if angular velocity falls steeply enough with radius, its surplus relative to its neighbours grows. The two effects feed each other, giving exponential growth while it beats viscous damping. They are killed by shear as well: it carries different radii at different speeds and shortens the radial wavelength, and viscous damping grows with the square of the wavenumber. The initial wavelength is chosen so that amplification wins first and damping inevitably later. Each pulse leaves a tail so small that all its derivatives vanish at the blowup time.

**The rest of the assembly.** There are two families of pulses: both the flux of angular momentum and the flux of axial momentum must be supplied, and the families differ in the ratio of the two. Toward the blowup the pulses are laid on ever finer grids in space and time, as in convex integration: an infinite ladder of corrections, each finer than the last. There is a deliberate asymmetry: with exact up-down symmetry the amplification mechanism vanishes in the plane z = 0, so the axial profile is slightly tilted. Outside the annulus the flow is purely azimuthal, independent of height, and solves the radial heat equation exactly: its residual is zero and no force is needed there. This allows a smooth spatial cutoff, and compactness carries the result to the torus, hence (D).

**What is new compared with predecessors.** The forcing-and-amplification-across-scales strategy belongs to Córdoba and Martínez-Zoroa: first for 3D Euler, then with Zheng for Navier–Stokes with weakened dissipation. Tao in 2016 built blowup for an averaged Navier–Stokes that keeps the energy cancellation. Two steps are new here: true viscosity and the full equation for every ν > 0, and pulses that do not merely amplify but act as a source of the required stress, fitted exactly under the hole in the background. The bricks are all known: centrifugal instability, wavevector transport by shear, exact viscous shearing waves, the realization of stress by oscillations from the Euler constructions of Daneri and Székelyhidi. Only the assembly is new.

**Who did it, and how.** By OpenAI's account, the proof was found by a group of about ten thousand coordinating agents on an internal model, in 88 hours, sending 2.7 million messages and spending about 130 billion output tokens; formalization and checking in Lean took another 17 hours. No human signs the paper: the author is listed as OpenAI. A day earlier Tristan Buckmaster and Levent Alpöge posted three preprints using the same smooth-forcing approach for the porous medium equation, Boussinesq and 3D Euler, also with Lean. A priority dispute arose; by mutual acknowledgement the proofs differ, and the Euler results themselves differ: forced on one side, unforced on the other.

**What remains open.** Starting from rest sounds dramatic but means the opposite of how it reads: since the fluid was still, all the energy came from the external force. The blowup here is not "order out of nothing" but a very precisely computed pumping. The unforced problem, alternatives (A) and (B), is unsolved, the Clay Institute lists it as open, and OpenAI says it will not claim the prize. But the pattern in which old tools are carried to the end by one machine and checked by another has now been tried on a problem that resisted people for ninety years.""",
    "fun_fact": "No human signed the paper: the author line reads OpenAI. Around ten thousand agents found the proof in 88 hours, and it was checked for 17 more hours not by a person but by Lean.",
    "scifi": "",
    "formulas": [
        {"description": "The residual as the definition of the force",
         "latex": r"f := \partial_t u + (u\cdot\nabla)u - \nu\Delta u + \nabla p",
         "meaning": "The flow is written down, the force is computed. The equation holds by construction; the task is to make f smooth while u → ∞."},
        {"description": "Scales of the needle and its energy",
         "latex": r"\ell_r\asymp\tau^{1/2},\ \ell_z\asymp\tau^{1/2-h},\ |u|\asymp\tau^{-1/2-h},\ E\asymp\tau^{1/2-3h}",
         "meaning": "As τ → 0 the speed diverges and the core energy tends to zero: the needle shrinks faster than it speeds up."},
        {"description": "Reynolds stress: a force out of oscillations",
         "latex": r"\langle u'_r u'_\theta\rangle \neq 0",
         "meaning": "A zero-mean oscillation transports angular momentum in one direction. This is how the pulses supply the force the background lacked."},
    ],
}

ADVANCED = {
    "title": "Finite-time blowup for the three-dimensional Navier–Stokes equations with a smooth compactly supported force: anatomy of the construction",
    "oneliner": "For every ν > 0: f ∈ C_c^∞ and a solution from rest with sup‖u‖_{L²} < ∞ and ‖u(t)‖_∞ → ∞ as t ↑ 1, settling Fefferman's alternatives (C) and (D). Proof scheme, scalings, the role of the pulses and the limits of the result.",
    "description": "Theorem 1.1: for every ν > 0 there exist a force f ∈ C_c^∞(R³×(0,∞); R³), a compact set K ⊂ R³ and smooth fields u, p on R³×[0,1) satisfying ∂_t u + (u·∇)u − νΔu + ∇p = f, ∇·u = 0, u(·,0) = 0, supported in K, with sup_{0≤t<1}‖u(t)‖_{L²} < ∞ and limsup_{t↑1}‖u(t)‖_{L^∞} = ∞. Consequently no smooth solution on R³×[0,∞) with the same force and data and uniformly bounded kinetic energy exists. This is alternative (C) of Fefferman's statement; compact support transfers the construction to T³ = R³/Z³ and gives (D). Released by OpenAI on 8 September 2026 together with a Lean 4 (Mathlib) formalization; no individual authors are listed.",
    "context": "The regularity problem asks whether a solution of the three-dimensional incompressible Navier–Stokes equations from smooth data stays smooth. Leray (1934) constructed global finite-energy weak solutions; Caffarelli, Kohn and Nirenberg (1982) showed the singular set of a suitable weak solution has zero one-dimensional parabolic Hausdorff measure, which allows isolated singularities; Escauriaza, Seregin and Šverák (2003) gave regularity under a bounded scale-invariant L^∞_t L³_x norm. Tao (2016) built blowup for averaged equations that keep the energy cancellation; Buckmaster and Vicol (2019) obtained nonuniqueness of weak solutions by convex integration; Albritton, Brué and Colombo (2022) built distinct Leray–Hopf solutions with zero data and one force, singular at the initial time. The direct predecessors are Córdoba and Martínez-Zoroa: blowup for forced 3D Euler (2023), for the porous medium equation with a smooth source (2024) and, with Zheng, for hypodissipative Navier–Stokes. In their constructions large-scale strain amplifies small-scale vorticity while self-interactions are suppressed. A day before OpenAI's paper, Buckmaster and Alpöge posted smooth-forcing blowup for the porous medium equation, 2D Boussinesq and 3D Euler with Lean formalizations; Tao the same day judged their approach 'likely to extend to Navier–Stokes'. Fefferman's statement explicitly accepts any of (A)–(D) as a solution; condition (5) on the force holds for every f ∈ C_c^∞.",
    "methods": "The method is inverse: the residual R(u,p) = ∂_t u + (u·∇)u − Δu + ∇p (ν = 1 after rescaling) is declared to be the force, and the task becomes constructing u, p with unbounded velocity and a residual smooth up to t = 1 together with all space-time derivatives. The construction is layered. (1) Axisymmetric self-similar background (u_B, p_B): in cylindrical coordinates a core with radial inflow, azimuthal spin-up and axial outflow on both sides of a dividing layer near z = 0; scales ℓ_r ≍ τ^{1/2}, ℓ_z ≍ τ^{1/2−h}, 0 < h < 1/100, speeds |u_θ|, |u_z| ≍ τ^{−1/2−h}, |u_r| = O(τ^{−1/2}); pressure decreases toward the axis and supplies the centripetal force; viscosity transports angular momentum outward, and the growth of speed is the balance of inflow against viscous loss. The profile equations impose the leading balance in the core; matching to a smooth exterior leaves in the annulus a residual equal to minus the divergence of an annular stress up to a term vanishing to every order at the singular point (Proposition 5.5). The axial profile is deliberately slightly asymmetric, with a small upward bias and u_z(r,0,t) ≠ 0: with exact symmetry both the axial transport of angular momentum and the radial shear of axial velocity would vanish at z = 0, and the pulses could not be amplified there. (2) Oscillatory pulses: sequences of spatially oscillating disturbances localized in r, z, t and closed into complete rings, two families with different ratios of radial angular-momentum flux to radial axial-momentum flux; their averaged quadratic products realize the leading stress (Proposition 7.5). The seed is an exponentially small external force; growth is on the background shear by the centrifugal mechanism (Leibovich–Stewartson, Billant–Gallaire criteria) with an axial-shear contribution; orientations are chosen so that shear shortens the radial wavelength, damping ∝ k² overtakes amplification, and the tails with all derivatives vanish as t → 1. The construction leans on the exact Craik–Criminale solutions and the Singh–Sridhar viscous shearing waves, and on the Daneri–Székelyhidi technique of realizing stresses by oscillations. (3) Successive corrections improve the decay of the residual (Proposition 9.6); an auxiliary torus and separation of oscillatory supports (Section 6); compactly supported mean corrections (Section 8). (4) The exterior flow is purely azimuthal, z-independent and solves the radial heat equation exactly (the 'heat exterior'): its residual vanishes identically; at every fixed r > 0 the fields and all derivatives have smooth limits as t ↑ 1, which allows a smooth spatial cutoff (Section 10); the cutoff force remains smooth. The estimates control every Cartesian derivative of the residual. The Lean 4 formalization with Mathlib (repository openai/NavierStokesAndEuler, Apache-2.0) covers the nonexistence of a global smooth solution with bounded energy on R³ and on the torus.",
    "results": "For every ν > 0: a smooth compactly supported finite-energy solution from rest with ‖u(t)‖_{L^∞} → ∞ as t ↑ 1, under a force f ∈ C_c^∞(R³×(0,∞)). Key scalings: core volume ≍ τ^{3/2−h}, core kinetic energy ≍ τ^{1/2−3h} → 0 with unbounded speed; Reynolds numbers Re_θ ≍ τ^{−h} → ∞ and Re_r = O(1); the rates |u_r|/ℓ_r, |u_z|/ℓ_z, ν/ℓ_r² are all ≍ τ^{−1}, axial diffusion weaker by τ^{2h}. Corollary 10.6: transfer to T³. Alternatives (C) and (D) of Fefferman's statement are claimed. OpenAI additionally reports blowup for the unforced Euler equations (a separate paper, ~100 agents, ~50 hours). By OpenAI's account: ~10,000 coordinating agents, 88 hours to the solution, 17 hours of Lean formalization and checking, 2.7 million messages, ~130 billion output tokens on this problem.",
    "implications": "The first example of finite-time blowup for the full three-dimensional Navier–Stokes equations with true viscosity and a smooth force, from rest and with finite energy. The mechanism is not an 'overcoming' of viscosity but its inclusion in a self-similar balance with a divergent rotational Reynolds number. It is shown constructively that the nonlinear term itself can supply the missing stress through the mean quadratic fluxes of oscillations, i.e. Reynolds stress acts as a controllable tool rather than a nuisance. For problem (A)/(B) the result gives no direct answer: the force is essential and the energy is injected from outside. But it moves the frontier: the unforced question becomes whether an analogous stress can arise from the initial data alone, without pumping. Separately significant is the methodological fact: a 166-page proof was assembled from known tools by a system of agents and checked formally; this is the first result of such weight published without a human signature.",
    "future_development": "Natural directions: an attempt to carry the construction to the unforced case, replacing pumping by energy stored in the initial data; the stability of the construction under perturbations and the size of h; a numerical illustration of the constructed flow; an independent human exposition of Sections 4–9; a comparison with the Buckmaster–Alpöge approach to see which parts coincide in substance. For hypodissipative and model equations the result will probably simplify existing constructions. Whether such pumping is physically realizable is also open: the force is mathematical, compact and smooth, but its physical counterpart is not discussed.",
    "impact_on": "Mathematical fluid dynamics (regularity, weak solutions, convex integration), the theory of vortex instabilities, formal verification of mathematics, the methodology of AI research. Indirectly, computational fluid dynamics: the construction provides an exact test case of concentration with divergent speed and vanishing energy.",
    "next_steps": "Read Section 2 (physical picture) and Section 3 (scheme) of the original; check conditions (4)–(7) against Fefferman's statement; look at the Lean repository and its README; read Tao's 7 September post on the Buckmaster–Alpöge papers and the Córdoba–Martínez-Zoroa preprints (arXiv:2309.08495, 2410.22920).",
    "key_problems_connection": "The Millennium Prize problem on Navier–Stokes existence and smoothness: alternatives (C) and (D) settled, (A) and (B) open. Related: Euler regularity (OpenAI reports unforced blowup; Buckmaster–Alpöge report blowup with smooth forcing), the Beale–Kato–Majda criterion, the conjectured finite-time Euler blowup from smooth data (numerical evidence by Luo–Hou, the Chen–Hou proof with boundary).",
    "fun_fact": "The background residual in the matching annulus diverges and cannot be fixed by an external force. It was fixed by the fluid: oscillations with zero mean velocity transport momentum in one direction, and that transport is fitted exactly under the hole. What turbulence theory calls a nuisance became a tool.",
    "scifi": "",
    "formulas": FORMULAS_ADV,
    "key_numbers": KEY_NUMBERS_ADV,
}

REVIEW = {
    "strength": "Inverting the problem: the flow is written down, the force is defined as the residual, and the whole difficulty is honestly moved into the smoothness of the residual. The self-limiting pulses that flare up on the shear and die out by viscosity, with their mean stress fitted to the divergence of the background, form a complete, checkable mechanism rather than an upper bound.",
    "advice": [
        "Give a human exposition of Sections 4–9 shorter than a hundred pages: the physics is clear in six pages, but the road from it to the estimates is open only formally.",
        "State explicitly what the Lean formalization covers (Theorem 1.1 in full or particular estimates) and how text and code correspond: without this 'checked in Lean' reads broader than it may be.",
        "A numerical illustration of the constructed flow on a finite τ horizon would show the scales and pulses visibly and give an independent check of the choice of h and wavelengths.",
        "Discuss which part of the construction is obstructed by the absence of a force: that is the only road from (C) to (A).",
    ],
    "questions": [
        "How stable is the construction under perturbations of the background and pulses: does blowup persist in an open neighbourhood of the constructed data?",
        "Does the self-feeding mechanism of the pulses give any hint for the unforced case, where the stress would have to arise from the initial data?",
        "What exactly is formalized in Lean: the full Theorem 1.1 with supports and estimates, or its nonexistence corollary?",
    ],
}

PROVENANCE = "made by OpenAI AI agents (≈10,000 agents, 88 h) · checked in Lean"

FIGURE_CAPTION = "Our diagram of the mechanism: fluid spirals toward the axis and flows out along it, the core contracts into a needle, and in the annulus around the core oscillatory pulses produce a mean stress that replaces the missing force. Outside, a purely azimuthal flow that needs no force."

SOURCE_LABELS = {"live": "paper page", "pdf": "PDF, 166 pp.", "repo": "Lean formalization"}

DATA = {
    "simple": SIMPLE, "popular": POPULAR, "advanced": ADVANCED, "abstract": ABSTRACT,
    "threads": THREADS, "review": REVIEW, "provenance": PROVENANCE,
    "figure_caption": FIGURE_CAPTION, "source_labels": SOURCE_LABELS,
}
