Objective    Optimize the prompt template in optimize.py to improve accuracy
             on AIME math problems. PROMPT_TEMPLATE instructs the model how
             to solve a problem and solve() uses it to get an answer.
Measured by  python evaluate.py, in the repository: accuracy on a subset of
             AIME 2024 problems, calling the OpenAI model it names
Baseline     about 0.10 to 0.20
Target       0.30 to 0.50, through the prompt alone
Rules
  - answers come in \boxed{XXX} form, a three-digit integer 000 to 999
  - only the prompt template and the logic around it in optimize.py change
  - evaluate.py is never modified
Budget       minutes=60 experiments=8
