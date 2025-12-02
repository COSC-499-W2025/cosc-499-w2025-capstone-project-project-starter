# Adding new datasets
New datasets and their respective categories should go in this directory. They should be named after the top level category they represent, for example "ai". Additionally, you need three files in the directory:

1. `./${dataset}/label_hier.txt` - Parent/child relationships for classes. Root class must be named ROOT. Tab delimited.
2. `./${dataset}/keywords.txt` - Class keywords, for leaves.
3. `./${dataset}/${json-name}.json` - JSON input, see the original repo for format.


Look at the HiGitClass README for more info.
