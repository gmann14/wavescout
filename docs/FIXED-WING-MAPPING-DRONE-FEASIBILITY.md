# Fixed-Wing Mapping Drone Feasibility for Nova Scotia Surf Recon

## Summary

For Nova Scotia surf reconnaissance, a DIY fixed-wing drone is viable as a repeatable coastal imaging platform, but it is not a dramatic upgrade over the existing `Mavic Pro`, `Mavic Air 2S`, and `Phantom 4 Pro` fleet for active swell capture.

The fixed wing would mainly add:

- longer flight times
- wider-area repeat passes over coastline and reefs
- autonomous capture of known spots and nearby prospects

It would not reliably solve:

- stitching active swell into useful orthomosaics
- tight launch and recovery constraints around surf zones
- logistics near cliffs, headlands, beaches, and changing wind

The best use case is to treat the aircraft as a repeatable shoreline and surf-state imaging tool, not a live water photogrammetry machine.

## Canada Constraints

As of `April 20, 2026`, the key Canadian constraints are still practical:

- Normal small-drone operations are capped at `122 m / 400 ft AGL` unless operating under a different authorization path.
- Site selection, airspace, NOTAMs, and nearby airport / heliport constraints still matter.
- Advanced and more complex operations depend on pilot certification, airspace authorization, and whether the aircraft has the required `Safety Assurance Declaration`.
- A self-built aircraft without the required declaration is effectively a basic-ops machine unless its builder takes on the compliance burden.

Relevant references:

- [Transport Canada: Where to fly your drone](https://tc.canada.ca/en/aviation/drone-safety/where-fly-your-drone)
- [Transport Canada: 2025 summary of drone regulation changes](https://tc.canada.ca/en/aviation/drone-safety/2025-summary-changes-canada-drone-regulations)
- [Transport Canada: Advanced operations](https://tc.canada.ca/en/aviation/drone-safety/learn-rules-you-fly-your-drone/drone-operation-categories-pilot-certificates/advanced-operations)
- [Transport Canada: Safety Assurance Declarations](https://tc.canada.ca/en/aviation/drone-safety/submitting-drone-safety-assurance-declaration)

## Why Swell Mapping Is Weak

Active water surfaces are still poor photogrammetry targets. Pix4D’s guidance remains consistent: water and other low-texture surfaces often fail calibration, and projects work better when each image contains substantial stable land detail.

That means:

- calm-day coastline and reef basemaps are realistic
- swell-day oblique documentation is realistic
- stitched maps of moving wave faces are not a strong primary deliverable

Reference:

- [Pix4D: No calibrated images](https://support.pix4d.com/hc/en-us/articles/8959364658077)

## Recommended Position

If the goal is pure operational value, standardizing data capture with the current DJI fleet is the better first move.

If the goal is also to build internal capability and a proprietary coastal image archive, a fixed-wing project is still worthwhile.

Recommended order:

1. Build and maintain a complete list of relevant Nova Scotia surf spots and high-likelihood prospects.
2. Standardize repeatable capture runs with current DJI aircraft.
3. Log each capture against swell direction, period, tide, wind, and output quality.
4. Add a fixed wing later to cover longer coastal transects and repeat passes.

## Build A: Around C$4k

This is the practical hobby-grade build that makes sense as a project.

### Target Use

- repeatable shoreline imaging
- oblique stills over known breaks
- prospect scouting on good swell windows

### Suggested Parts

- Airframe: [XFLY X2100 FPV Glider Twin PNP](https://www.greathobbies.com/productinfo/?prod_id=XFM113PX) — `C$349.99`
- Autopilot: [Holybro Pixhawk 6C + PM02 + M10 GPS](https://dronedynamics.ca/products/pixhawk-6c) — `C$294.99`
- Radio: [RadioMaster Boxer ELRS](https://rotorvillage.ca/radiomaster-boxer-transmitter-elrs/) — about `C$195.99`
- Receiver: [BetaFPV SuperP 14CH Diversity Receiver](https://dronedynamics.ca/products/betafpv-superp-14ch-diversity-receiver) — `C$44.99`
- Telemetry: [MicoAir LR-900F](https://dronedynamics.ca/products/lr-900f-telemetry-radio) — `C$73.99`
- Airspeed sensor: [Holybro MS5525DSO](https://dronedynamics.ca/products/19010) — `C$89.99`
- Charger: [HOTA H6 Pro](https://dronedynamics.ca/products/hota-h6-pro-ac-dc-charger) — `C$130.99`
- Batteries: two [GNB 5200mAh 6S LiHV packs](https://dronedynamics.ca/products/gnb-lihv-6s-22-8v-5200mah-120c-lipo-battery-xt60) — `C$158.99` each
- Camera: [Sony ZV-E10 kit with 16-50mm lens](https://www.vistek.ca/store/446376/Alpha-ZV-E10-Mirrorless-Kit-Black-w-SEL-16-50mm--PZ-Lens) — `C$999.99`

### Budget Reality

Expected real cost after mount hardware, trigger setup, cards, spares, adhesives, and inevitable setup waste:

- pre-tax: roughly `C$3.3k-C$3.9k`
- with Nova Scotia `15% HST`: roughly `C$3.8k-C$4.5k`

### Expected Outcome

This should be viewed as a capable prototype, not a production mapping aircraft.

Likely value:

- wider coverage than a quad on each run
- more repeatable autonomous passes
- stronger long-term archive collection workflow

Likely limitations:

- no meaningful orthomosaic advantage on active swell
- harder field ops than the DJI fleet
- higher risk on launch, landing, and payload damage

## Build B: Around C$7k

This only starts to make sense if the goal is to carry a materially better stills payload and prove a more serious fixed-wing pipeline.

### Suggested Parts

- Airframe: same class as Build A to keep the stack realistic at hobby scale
- Autopilot: [Holybro Pixhawk 6X V2A + M10 + PM20D](https://dronedynamics.ca/products/pixhawk-6x-v2a-m10-gps-pm20d) — `C$445.99`
- Airspeed sensor: [Holybro DroneCAN DLVR](https://dronedynamics.ca/products/high-precision-dronecan-airspeed-sensor-dlvr-sensor-w-pt40-pitot-tube) — `C$154.99`
- Charger: [HOTA D6 Pro](https://dronedynamics.ca/products/hota-d6-pro-ac-200w-dc-325wx2-15ax2-dual-channel-smart-battery-charger) — `C$175.99`
- Payload camera: [Sony ILX-LR1](https://www.vistek.ca/store/462314/sony-ilxlr1-industrial-camera) — `C$3,890.00`
- Lens: [Sony FE 24mm f/2.8 G](https://www.vistek.ca/store/444192/sony-sel-fe-24mm-f28-g-emount-lens) — `C$799.99`

### Budget Reality

Expected total:

- pre-tax: roughly `C$6.9k-C$7.3k`
- with Nova Scotia `15% HST`: roughly `C$7.9k-C$8.4k`

### Expected Outcome

This is the first version that has a clear daylight still-image quality case over the current consumer DJI fleet.

But it also becomes much easier to build the wrong aircraft:

- the payload becomes expensive enough that crash risk matters a lot
- hobby-grade airframes become less comfortable choices
- it makes less sense to buy this camera before the aircraft is already flying well with ballast

## Bottom Line

For the specific surf use case:

- The fixed wing is a good project.
- It is a moderate data-gathering upgrade, not a transformative one.
- The current DJI fleet is still the better tool for tactical day-of surf capture.
- A fixed wing becomes most useful once there is already a disciplined spot list, capture plan, and metadata workflow.

The strongest version of the idea is:

- build the Nova Scotia spot database
- capture repeatable reference imagery of known spots
- revisit high-likelihood prospects under target swell windows
- use land-anchored imagery and oblique passes instead of trying to map moving surf directly
