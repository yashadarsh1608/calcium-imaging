# Method

Everything is done **per cell** and **per movie**; each movie has its own baseline.

## Background subtraction

For every frame *t*:

$$X(t) = I_\text{cell}(t) - \overline{I}_\text{background}(t)$$

where $\overline{I}_\text{background}$ is the mean of the chosen background boxes in that frame. This
removes the camera offset (~100 gray values) and changes in stray light.

## Baseline and ΔF

$$B_\text{avg} = \frac{1}{n_b}\sum_{t \in \text{baseline}} X(t) \qquad \Delta F(t) = X(t) - B_\text{avg}$$

## Responder threshold

$$\text{SD} = \operatorname{sd}\big(\Delta F(t),\ t \in \text{baseline}\big)\ \text{(sample SD, } n-1\text{)}$$

$$\text{threshold} = \overline{\Delta F}_\text{baseline} + N \cdot \text{SD} \qquad (N = 5 \text{ by default})$$

$$\text{mean peak} = \frac{1}{n_p}\sum_{t \in \text{peak window}} \Delta F(t)$$

A cell is a **responder** to a drug if *mean peak > threshold*. The threshold is set for each cell from
its own noise, so a quiet cell needs a smaller rise than a noisy one.

## Normalised responses

$$\Delta F/F_0 = \frac{\Delta F(t)}{B_\text{avg}}$$

(only for cells brighter than background at rest, $B_\text{avg} > 0$).

With a quality-control drug (QC, e.g. KCl or ionomycin):

- **kept** = responder to the QC drug; only kept cells are analysed and counted.
- $\Delta F / \Delta F_\text{QC} = \Delta F(t) \,/\, \text{mean peak}_\text{QC}$ of the same cell: the
  response as a fraction of that cell's QC response. KCl is not a true maximum, so values above 1 are
  possible.

## Averages

Mean traces are averaged over cells; error = SD across cells or SEM = SD / √n.
Percentages are of the analysed (kept) cells.

## Cell size

From the ImageJ outline: area; equivalent diameter $= 2\sqrt{\text{area}/\pi}$; Feret diameters
(longest / shortest width); perimeter; circularity $= 4\pi \cdot \text{area}/\text{perimeter}^2$.
Values are as good as the segmentation.

## Experiment time

Movie *k* starts at the sum of the lengths of the earlier movies plus the washing times in between, so
traces from different movies line up on one time axis with the washes as gaps.
