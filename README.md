# Python Project 3A

The main repository for the third year python project, group 7

## Members (Mapping between usernames and members of the group)

| Username          | Name                              |
| ----------------- | --------------------------------- |
| Shadow            | SCHREYECK Romain                  |
| Friedrich482      | WEKENON TOKPONTO Sedjro Friedrich |
| manuvall2         | Manuel VALLEDOR                   |
| memenikoi         | Emir REKIKI                       |
| isselmouabdijiyed | ABDI OULD JIYID Isselmou          |
| ibounass21        | ABDOUL NASSIROU GARBA Ibrahim     |
| .                 | TRAN HUU QUANG Vinh               |

## Project setup

- Clone the repository:

  ```bash
  git clone https://github.com/Python-project-3A/python-project-3A.git
  ```

- run `pip install contourpy cycler fonttools keyboard kiwisolver   matplotlib
numpy
packaging
pillow
pygame
pyparsing
python-dateutil
ruff
screeninfo
six` to install the dependencies

## All commands

- Run a scenario in terminal mode

  ```bash
  python3 -m src.main run <scenario> <general1> <general2> -t
  ```

- Run a scenario in graphical mode

  ```bash
  python3 -m src.main run <scenario> <general1> <general2> -gui
  ```

- Run a scenario in headless mode

  ```bash
  python3 -m src.main run <scenario> <general1> <general2>
  ```

- Load a save

  ```bash
  python3 -m src.main load <save_name>
  ```

- Tournament

  ```bash
  python3 -m src.main tourney -S <scenarios> -G <generals> -N <number_of_games> -na <dont_alternate_units_positions>
  ```

- List all scenarios

  ```bash
  python3 -m src.main list
  ```

- Plot Lanchester

  ```bash
  python3 -m src.main plot [-h] <unit_type> <min_n> <max_n> <step>
  ```

## Commands we used for the presentation
