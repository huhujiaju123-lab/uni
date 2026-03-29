globals [
  gini-index-reserve
  lorenz-points
  target-ticks
]

turtles-own [
  sugar
  metabolism
  vision
  vision-points
  age
  max-age
]

patches-own [
  psugar
  max-psugar
]

to setup
  clear-all
  set target-ticks 7400
  create-turtles 1000 [ turtle-setup ]
  setup-patches
  update-lorenz-and-gini
  reset-ticks
end

to turtle-setup
  set color red
  set shape "circle"
  move-to one-of patches with [not any? other turtles-here]
  set sugar random-in-range 4 65
  set metabolism random-in-range 1 4
  set max-age random-in-range 60 100
  set age 0
  set vision 3  ;; FIXED TO 3 FOR EXPERIMENT A
  set vision-points []
  foreach (range 1 (vision + 1)) [ n ->
    set vision-points sentence vision-points (list (list 0 n) (list n 0) (list 0 (- n)) (list (- n) 0))
  ]
end

to setup-patches
  file-open "/Applications/NetLogo 7.0.3/models/Sample Models/Social Science/Economics/Sugarscape/sugar-map.txt"
  foreach sort patches [ p ->
    ask p [
      set max-psugar file-read
      set psugar max-psugar
      patch-recolor
    ]
  ]
  file-close
end

to go
  if not any? turtles or ticks >= target-ticks [
    print (word "Experiment A Complete! Final Gini Index: " ((gini-index-reserve / count turtles) * 2))
    stop
  ]
  ask patches [
    patch-growback
    patch-recolor
  ]
  ask turtles [
    turtle-move
    turtle-eat
    set age (age + 1)
    if sugar <= 0 or age > max-age [
      hatch 1 [ turtle-setup ]
      die
    ]
  ]
  update-lorenz-and-gini
  tick
  if ticks mod 1000 = 0 [
    print (word "Progress: " ticks " / " target-ticks " ticks, Current Gini: " ((gini-index-reserve / count turtles) * 2))
  ]
end

to turtle-move
  let move-candidates (patch-set patch-here (patches at-points vision-points) with [not any? turtles-here])
  let possible-winners move-candidates with-max [psugar]
  if any? possible-winners [
    move-to min-one-of possible-winners [distance myself]
  ]
end

to turtle-eat
  set sugar (sugar - metabolism + psugar)
  set psugar 0
end

to patch-recolor
  set pcolor (yellow + 4.9 - psugar)
end

to patch-growback
  set psugar min (list max-psugar (psugar + 1))
end

to update-lorenz-and-gini
  let num-people count turtles
  let sorted-wealths sort [sugar] of turtles
  let total-wealth sum sorted-wealths
  let wealth-sum-so-far 0
  let index 0
  set gini-index-reserve 0
  set lorenz-points []
  repeat num-people [
    set wealth-sum-so-far (wealth-sum-so-far + item index sorted-wealths)
    set lorenz-points lput ((wealth-sum-so-far / total-wealth) * 100) lorenz-points
    set index (index + 1)
    set gini-index-reserve
      gini-index-reserve +
      (index / num-people) -
      (wealth-sum-so-far / total-wealth)
  ]
end

to-report random-in-range [low high]
  report low + random (high - low + 1)
end
