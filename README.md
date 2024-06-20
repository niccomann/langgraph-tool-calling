
# Installation Guide

Follow these steps to set up your environment and start the engine:

## Step 1: Configuration
Update the `.env` file with your OpenAI API key:
```
OPENAI_API_KEY=xxxxxxx
```

## Step 2: Install Dependencies
Run the following command to install the necessary packages:
```
pip install -r requirements.txt
```

## Step 3: Database Setup
Create and populate the database using:
```
python create_db_mock_user_order.py
```

## Step 4: Start the Engine
Launch the application by executing:
```
python chart_generator_advanced.py
```

