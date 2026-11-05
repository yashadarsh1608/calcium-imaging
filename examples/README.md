# Example data (synthetic)

`data/` holds **made-up** data in the format Fiji writes: three drug movies, one KCl quality-control
movie (97 cells + 3 background boxes, 50 frames each) and a cell size file in pixels (0.5 µm per pixel).
No real experiment data is in this repository.

Run the whole analysis without typing:

```bash
cd examples/data
python ../../scripts/calcium_multidrug.py < ../answers_example.txt
python ../../scripts/make_graphs.py        # press ENTER at every question
```

`answers_example.txt` has one answer per line, in the order the script asks
(see [docs/05_python_analysis.md](../docs/05_python_analysis.md)). To make new example data:
`python examples/generate_example_data.py`.
