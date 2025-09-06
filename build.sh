#!/bin/bash
# build.sh

# Fix deprecated joblib import in profanity_check
sed -i 's/from sklearn.externals import joblib/import joblib/' \
  .venv/lib/python3.13/site-packages/profanity_check/profanity_check.py
