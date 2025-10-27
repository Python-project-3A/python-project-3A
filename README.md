# Python Project 3A

The main repository for the third year python project, group 7

## Project setup

When you clone or pull the latest changes of this repository, you want to:

- place yourself at the root of the directory
- create a virtual environment if you haven't yet: `python3 -m venv .venv`. This will add a `.venv` directory at the root of the project:

  <img width="232" height="30" alt="Screenshot from 2025-10-27 16-18-13" src="https://github.com/user-attachments/assets/cb111553-d164-48f1-9256-bc7446c3b431" />
- activate it : `source .venv/bin/activate`. Now in your terminal it should show `(.venv)` before the prompt:
  
  <img width="135" height="41" alt="Screenshot from 2025-10-27 16-31-52" src="https://github.com/user-attachments/assets/db165022-241f-4862-91a6-32fdcc0e9077" />

- run `pip install -r requirements.txt` to install the dependencies

## Linting/Formatting commands

- lint the code (reveal the syntax errors): `ruff check .`
- and to format the code properly: `ruff format .`
