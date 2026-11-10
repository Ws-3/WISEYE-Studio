# WISEYE native JSBSim adapter

Release v1.1.0 (2026-11-10): the source plugin bundle includes the adapter runtime, model XML and licenses. Both canonical and custom-host build receipts stage runtime resources. Custom-host Editor flight and Shipping compilation passed; a cooked custom-host flight has not been validated. The reference aircraft remains uncalibrated. See [distribution guide](../../docs/PLUGIN_DISTRIBUTION.md).

This small DLL embeds the unmodified JSBSim 1.2.4 core, pinned to
`e07a7d810d4f1048039d42545d008b8a998636fa` from
<https://github.com/JSBSim-Team/jsbsim>.

Build with `scripts/Build-JSBSim.ps1` (MSVC x64 and CMake). The script downloads
the pinned source under `builds/dependencies`, verifies the commit, builds the
adapter and places the runtime under `ue5/WISEYE/ThirdParty/JSBSim`. The C ABI
is defined in `ue5/WISEYE/Source/test/WiseEyeJSBSimAPI.h`. UE dynamically loads
this replaceable DLL; it does not link directly against JSBSim C++ classes.
The ProjectAirSim dependency's own JSBSim library is untouched.

JSBSim is LGPL-2.1-or-later; its license accompanies the runtime. The upstream
source is unmodified. All WISEYE adapter source and the complete aircraft XML
are included here/in the runtime resource tree to permit rebuilding. The UE
build receipt stages the DLL, aircraft model and license as NonUFS resources.

The generic `wiseye80` model is **uncalibrated**. Mass, inertia, wing area,
aerodynamic coefficients and thrust are engineering estimates. Only the visual
length and inferred wingspan follow the user's FBX. It is not an identified
aircraft model. The electric thrust model is a lagged force, not a calibrated
propeller/motor map. Integration is fixed at 120 Hz; the adapter implements
assisted speed, bank and climb commands using aileron/elevator/rudder inputs.
The FDM uses a 500 m reference atmosphere and local NED velocity integration
to UE centimeters. UE handles building collision. Ground handling, weather/wind
coupling and direct unassisted surface controls are not implemented.

`tests/test_jsbsim_native.py` exercises the actual DLL; `tests/verify_jsbsim_camera_live.py`
validates its UE/Qt integration using an isolated data directory.
