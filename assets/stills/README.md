# Local still images

Put three legally usable still images for each movie in this folder, using the paths listed in `movies.json`, for example:

```text
citizen-kane-1.jpg
citizen-kane-2.jpg
citizen-kane-3.jpg
```

The mailer embeds files from this folder as inline CID images. Missing files are skipped so the workflow will not fail.

Use `required-stills.txt` as the full checklist. After adding images, run:

```text
python tools/check_stills.py
```

The checker prints how many images exist and which filenames are still missing.

Only commit images you have permission to store and redistribute. Good sources include public-domain images, Creative Commons images whose license allows your use, official press-kit images that explicitly allow redistribution, or image files you personally have rights to use.
