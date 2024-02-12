# Snake Game
A basic implementation of the classic Snake Game in Python making use of Pygame.

### Setting up
- Must have [Python](https://www.python.org) installed.
- Must have [Pygame](https://www.pygame.org/wiki/about) installed.
- You must have MySQL installed in your machine;
- You must create a schema under the name of ```snake_game```;
- Create the following table(s):
  - "scores": user_name (Primary Key, Text), score (Int)

After doing so you must open main.py file and modify the database access credentials, ```DATABASE_USER``` and ```DATABASE_PASSWORD```to match your access credentials.

Once everything is set up, all you have to do is run main.py via:
```
python path\to\project main.py
```
