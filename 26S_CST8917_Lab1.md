# Lab 1: Create and Deploy Your First Azure Function

## CST8917 - Serverless Applications | Summer 2026

---

## Overview

In this lab, you will create your first Azure Function using Visual Studio Code and deploy it to Azure. This hands-on exercise introduces you to the complete serverless development workflow: from creating a local project to testing and deploying to the cloud.

**What You'll Learn:**
- Set up your development environment for Azure Functions
- Create an HTTP-triggered function using VS Code
- Run and test functions locally
- Deploy functions to Azure
- Test your deployed function in the cloud

---

## Part 1: Prerequisites

Before starting this lab, ensure you have the following installed and configured:

### Required Software

| Tool                          | Description                           | Installation Link                                        |
| ----------------------------- | ------------------------------------- | -------------------------------------------------------- |
| **Azure Account**             | An active Azure subscription          | [Create free account](https://azure.microsoft.com/free/) |
| **Visual Studio Code**        | Code editor                           | [Download VS Code](https://code.visualstudio.com/)       |
| **Azure Functions Extension** | VS Code extension for Azure Functions | Install from VS Code Extensions                          |
| **Python 3.12**               | Programming language runtime          | [Install Python](https://www.python.org/downloads/)      |
| **Python Extension**          | VS Code extension for Python          | Install from VS Code Extensions                          |

### Verify Your Setup

1. Open VS Code
2. Press `F1` to open the Command Palette
3. Type "Python: Select Interpreter" and verify Python 3.12 is available
4. Type "Azure Functions" and verify the extension commands appear

---

## Part 2: Install or Update Azure Functions Core Tools

The Azure Functions Core Tools allow you to run and debug functions locally before deploying to Azure.

### Steps:

1. In Visual Studio Code, press `F1` to open the Command Palette

2. Search for and run: **Azure Functions: Install or Update Core Tools**

3. Wait for the installation to complete

> **Note:** If you don't have npm or Homebrew installed, you may need to [manually install Core Tools](https://learn.microsoft.com/azure/azure-functions/functions-run-local).

---

## Part 3: Create Your Local Function Project

In this section, you'll create a new Azure Functions project with an HTTP-triggered function.

### Step 3.1: Create New Project

#### Option A: Using VS Code

1. Press `F1` to open the Command Palette

2. Search for and run: **Azure Functions: Create New Project...**

3. Choose a directory location for your project:
   - Create a new folder or select an empty folder
   - **Important:** Don't choose a folder that's already part of another workspace

#### Option B: Using the Command Line (Alternative)

If you prefer using the terminal, you can create the project with Azure Functions Core Tools:

```bash
# Create a new folder and navigate into it
mkdir MyFunctionProject
cd MyFunctionProject

# Initialize the Functions project with Python
func init --python

# Create an HTTP-triggered function named HttpExample
func new --name HttpExample --template "HTTP trigger" --authlevel anonymous
```

> **Note:** After using the CLI approach, open the folder in VS Code with `code .` to continue with the rest of the lab.

### Step 3.2: Configure Project Settings

If you chose **Option A** (VS Code), provide the following information when prompted:

| Prompt                          | Your Selection                                              |
| ------------------------------- | ----------------------------------------------------------- |
| **Select a language**           | `Python`                                                    |
| **Select a Python interpreter** | Choose your Python 3.12 interpreter (or type the full path) |
| **Select a template**           | `HTTP trigger`                                              |
| **Name of the function**        | `HttpExample`                                               |
| **Authorization level**         | `anonymous`                                                 |
| **Open project**                | `Open in current window`                                    |

If you chose **Option B** (CLI), these settings were already configured via the command flags.

### Understanding the Project Structure

After VS Code creates your project, you'll see the following files and folders:

```
📁 YourProjectFolder/
├── 📁 .venv/                  # Python virtual environment (auto-created)
├── 📁 .vscode/                # VS Code configuration files
│   ├── extensions.json        # Recommended extensions
│   ├── launch.json            # Debug configuration
│   ├── settings.json          # Project settings
│   └── tasks.json             # Build tasks
├── .funcignore                # Files to exclude from deployment
├── .gitignore                 # Files to exclude from Git
├── function_app.py            # Your function code (main file)
├── host.json                  # Global configuration for all functions
├── local.settings.json        # Local environment settings (not deployed)
└── requirements.txt           # Python package dependencies
```

#### Key Files Explained

| File                    | Purpose                                                                                                                                   |
| ----------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| **function_app.py**     | Contains your function code. This is where you define HTTP triggers and write your business logic using the Python v2 programming model.  |
| **host.json**           | Global configuration options that affect all functions in the app (logging, extensions, etc.).                                            |
| **local.settings.json** | Stores app settings and connection strings for local development. **Never commit this file to source control** as it may contain secrets. |
| **requirements.txt**    | Lists Python packages your function needs. Azure installs these during deployment.                                                        |
| **.funcignore**         | Similar to `.gitignore`, specifies files that should NOT be uploaded when deploying to Azure.                                             |

> **Note:** The `.venv` folder contains your Python virtual environment. VS Code automatically activates this environment when you open the project.

### Step 3.3: Configure Local Storage

Azure Functions requires a storage account to manage triggers, logging, and other internal operations. When developing locally, instead of connecting to a real Azure Storage account, we use **Azurite** - a local storage emulator that simulates Azure Storage on your machine.

1. In VS Code Explorer, click on `local.settings.json` to open it

2. You should see something like this:
   ```json
   {
     "IsEncrypted": false,
     "Values": {
       "FUNCTIONS_WORKER_RUNTIME": "python",
       "AzureWebJobsStorage": ""
     }
   }
   ```

3. Update the `AzureWebJobsStorage` value from empty `""` to `"UseDevelopmentStorage=true"`:

   ```json
   {
     "IsEncrypted": false,
     "Values": {
       "FUNCTIONS_WORKER_RUNTIME": "python",
       "AzureWebJobsStorage": "UseDevelopmentStorage=true"
     }
   }
   ```

4. Save the file (`Ctrl + S`)

#### What do these settings mean?

| Setting                    | Purpose                                                                                          |
| -------------------------- | ------------------------------------------------------------------------------------------------ |
| `IsEncrypted`              | When `false`, settings are stored in plain text (fine for local dev)                             |
| `FUNCTIONS_WORKER_RUNTIME` | Tells Azure Functions which language runtime to use                                              |
| `AzureWebJobsStorage`      | Connection string for storage. `UseDevelopmentStorage=true` points to the local Azurite emulator |

> **Important:** The `local.settings.json` file is listed in `.gitignore` by default. This is intentional - when you deploy to Azure, you'll use real connection strings that should never be committed to source control.

---

## Part 4: Start the Azurite Storage Emulator

Before running your function locally, you need to start the storage emulator.

#### Option A: Using VS Code

1. Press `F1` to open the Command Palette

2. Search for and select: **Azurite: Start**

3. Check the bottom status bar - verify that Azurite emulation services are running

#### Option B: Using the Command Line

If you prefer the terminal, first install Azurite globally (one-time setup):

```bash
npm install -g azurite
```

Then start Azurite:

```bash
azurite --silent --location .azurite --debug .azurite/debug.log
```

| Flag         | Purpose                          |
| ------------ | -------------------------------- |
| `--silent`   | Suppresses verbose output        |
| `--location` | Directory to store emulator data |
| `--debug`    | Path for debug log file          |

> **Tip:** Run Azurite in a separate terminal window so it stays running while you work.

> **Checkpoint:** You should see indicators in VS Code's status bar (Option A) or a message in the terminal (Option B) showing Azurite is active.

---

## Part 5: Run and Test Your Function Locally

### Step 5.1: Start the Function

#### Option A: Using VS Code

1. Press `F5` or click the **Run and Debug** icon in the Activity bar

2. Watch the **Terminal** panel for output from Core Tools

#### Option B: Using the Command Line

```bash
func start
```

> **Tip:** Use `func start --verbose` for more detailed output when debugging issues.

---

Regardless of which option you chose, look for the local URL endpoint in the output:

```
Functions:
     HttpExample: [GET,POST] http://localhost:7071/api/HttpExample
```

> **Troubleshooting (Windows):** If you have trouble running, ensure VS Code's default terminal is NOT set to WSL Bash.

### Step 5.2: Test the Function

With Core Tools still running in the terminal, choose one of the following methods to test your function:

#### Option A: Using VS Code Azure Extension

1. Click the **Azure icon** in the Activity bar

2. In the **Workspace** area, expand **Local Project** > **Functions**

3. Right-click (Windows) or Ctrl-click (macOS) on `HttpExample`

4. Select **Execute Function Now...**

5. In the **Enter request body** prompt, you'll see:
   ```json
   { "name": "Azure" }
   ```

6. Press **Enter** to send the request

7. A notification will appear with the function's response

#### Option B: Using curl (Command Line)

Open a new terminal and run:

```bash
# GET request with query parameter
curl "http://localhost:7071/api/HttpExample?name=Azure"

# POST request with JSON body
curl -X POST http://localhost:7071/api/HttpExample \
  -H "Content-Type: application/json" \
  -d '{"name": "Azure"}'
```

#### Option C: Using a Browser

For simple GET requests, open your browser and navigate to:

```
http://localhost:7071/api/HttpExample?name=Azure
```

#### Option D: Using VS Code REST Client Extension

1. Install the **REST Client** extension in VS Code

2. Create a file named `test.http` in your project folder:

   ```http
   ### Test GET request
   GET http://localhost:7071/api/HttpExample?name=Azure

   ### Test POST request
   POST http://localhost:7071/api/HttpExample
   Content-Type: application/json

   {
     "name": "Azure"
   }
   ```

3. Click **Send Request** above each request to execute it

### Step 5.3: Stop the Function

1. Click in the **Terminal** panel

2. Press `Ctrl + C` to stop Core Tools and disconnect the debugger

---

## Part 6: Implement the Text Analyzer Function

Now let's replace the default template code with a real-world function that analyzes text.

> **Important:** This new code replaces the `HttpExample` function with a `TextAnalyzer` function. After this change, your endpoint URL will change from:
> - **Before:** `http://localhost:7071/api/HttpExample`
> - **After:** `http://localhost:7071/api/TextAnalyzer`

### Step 6.1: Open the Function Code

1. In VS Code Explorer, open `function_app.py`

2. You'll see the default template code (the `HttpExample` function that returns a greeting)

### Step 6.2: Replace with Text Analyzer Code

Replace the **entire contents** of `function_app.py` with the following code:

```python
# =============================================================================
# IMPORTS - Libraries we need for our function
# =============================================================================
import azure.functions as func  # Azure Functions SDK - required for all Azure Functions
import logging                  # Built-in Python library for printing log messages
import json                     # Built-in Python library for working with JSON data
import re                       # Built-in Python library for Regular Expressions (pattern matching)
from datetime import datetime   # Built-in Python library for working with dates and times

# =============================================================================
# CREATE THE FUNCTION APP
# =============================================================================
# This creates our Function App with anonymous access (no authentication required)
# Think of this as the "container" that holds all our functions
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# =============================================================================
# DEFINE THE TEXT ANALYZER FUNCTION
# =============================================================================
# The @app.route decorator tells Azure: "When someone visits /api/TextAnalyzer, run this function"
# This is called a "decorator" - it adds extra behavior to our function
@app.route(route="TextAnalyzer")
def TextAnalyzer(req: func.HttpRequest) -> func.HttpResponse:
    """
    This function analyzes text and returns statistics about it.

    Parameters:
        req: The incoming HTTP request (contains the text to analyze)

    Returns:
        func.HttpResponse: JSON response with analysis results
    """

    # Log a message so we can see in Azure Portal when the function is called
    logging.info('Text Analyzer API was called!')

    # =========================================================================
    # STEP 1: GET THE TEXT INPUT
    # =========================================================================
    # First, try to get 'text' from the URL query string
    # Example URL: /api/TextAnalyzer?text=Hello world
    # req.params.get('text') would return "Hello world"
    text = req.params.get('text')

    # If text wasn't in the URL, try to get it from the request body (JSON)
    if not text:
        try:
            # Try to parse the request body as JSON
            # Example body: {"text": "Hello world"}
            req_body = req.get_json()
            text = req_body.get('text')
        except ValueError:
            # If the body isn't valid JSON, just continue (text stays None)
            pass

    # =========================================================================
    # STEP 2: ANALYZE THE TEXT (if text was provided)
    # =========================================================================
    if text:
        # ----- Word Analysis -----
        # split() breaks the text into a list of words
        # "Hello world" becomes ["Hello", "world"]
        words = text.split()

        # len() counts items in a list
        # ["Hello", "world"] has length 2
        word_count = len(words)

        # ----- Character Analysis -----
        # len() on a string counts characters (including spaces)
        # "Hello world" has 11 characters
        char_count = len(text)

        # replace(" ", "") removes all spaces, then we count
        # "Hello world" becomes "Helloworld" (10 characters)
        char_count_no_spaces = len(text.replace(" ", ""))

        # ----- Sentence Analysis -----
        # re.findall() finds all matches of a pattern
        # r'[.!?]+' means: find any sequence of periods, exclamation marks, or question marks
        # "Hello! How are you?" returns ['!', '?'] (2 sentences)
        # The "or 1" means: if no punctuation found, assume at least 1 sentence
        sentence_count = len(re.findall(r'[.!?]+', text)) or 1

        # ----- Paragraph Analysis -----
        # Paragraphs are separated by blank lines (two newlines: \n\n)
        # split('\n\n') breaks text at blank lines
        # We filter out empty paragraphs with "if p.strip()"
        # strip() removes whitespace - empty strings become "" which is False
        paragraph_count = len([p for p in text.split('\n\n') if p.strip()])

        # ----- Reading Time Calculation -----
        # Average reading speed is about 200 words per minute
        # round(x, 1) rounds to 1 decimal place
        # 100 words / 200 wpm = 0.5 minutes
        reading_time_minutes = round(word_count / 200, 1)

        # ----- Average Word Length -----
        # Total characters (no spaces) divided by number of words
        # We check "if word_count > 0" to avoid dividing by zero
        avg_word_length = round(char_count_no_spaces / word_count, 1) if word_count > 0 else 0

        # ----- Find Longest Word -----
        # max() finds the largest item
        # key=len means "compare words by their length"
        # max(["Hi", "Hello", "Hey"], key=len) returns "Hello"
        longest_word = max(words, key=len) if words else ""

        # =====================================================================
        # STEP 3: BUILD THE RESPONSE
        # =====================================================================
        # Create a Python dictionary with all our analysis results
        # This will be converted to JSON format
        response_data = {
            "analysis": {
                "wordCount": word_count,
                "characterCount": char_count,
                "characterCountNoSpaces": char_count_no_spaces,
                "sentenceCount": sentence_count,
                "paragraphCount": paragraph_count,
                "averageWordLength": avg_word_length,
                "longestWord": longest_word,
                "readingTimeMinutes": reading_time_minutes
            },
            "metadata": {
                # datetime.utcnow() gets current time, isoformat() converts to string
                # Example: "2024-01-15T14:30:00.000000"
                "analyzedAt": datetime.utcnow().isoformat(),

                # Show first 100 characters of text as a preview
                # The syntax: value_if_true if condition else value_if_false
                # This is called a "ternary operator" or "conditional expression"
                "textPreview": text[:100] + "..." if len(text) > 100 else text
            }
        }

        # Return a successful HTTP response
        # json.dumps() converts Python dictionary to JSON string
        # indent=2 makes the JSON nicely formatted (2 spaces per indent level)
        # mimetype tells the browser "this is JSON data"
        # status_code=200 means "OK - Success"
        return func.HttpResponse(
            json.dumps(response_data, indent=2),
            mimetype="application/json",
            status_code=200
        )

    # =========================================================================
    # STEP 4: HANDLE MISSING TEXT (Error Response)
    # =========================================================================
    else:
        # If no text was provided, return helpful instructions
        instructions = {
            "error": "No text provided",
            "howToUse": {
                "option1": "Add ?text=YourText to the URL",
                "option2": "Send a POST request with JSON body: {\"text\": \"Your text here\"}",
                "example": "https://your-function-url/api/TextAnalyzer?text=Hello world"
            }
        }

        # Return an error response
        # status_code=400 means "Bad Request - client made an error"
        return func.HttpResponse(
            json.dumps(instructions, indent=2),
            mimetype="application/json",
            status_code=400
        )
```

### Step 6.3: Save and Restart

1. Save the file (`Ctrl + S`)

2. If the function is running, stop it (`Ctrl + C` in terminal)

3. Start the function again using `func start` or `F5`

### Step 6.4: Test the Text Analyzer

Test your new function using any of the methods from Step 5.2:

**Using curl:**
```bash
curl "http://localhost:7071/api/TextAnalyzer?text=Serverless%20computing%20is%20amazing.%20It%20scales%20automatically."
```

**Using browser:**
```
http://localhost:7071/api/TextAnalyzer?text=Serverless computing is amazing. It scales automatically.
```

**Expected Response:**
```json
{
  "analysis": {
    "wordCount": 7,
    "characterCount": 56,
    "characterCountNoSpaces": 49,
    "sentenceCount": 2,
    "paragraphCount": 1,
    "averageWordLength": 7.0,
    "longestWord": "automatically.",
    "readingTimeMinutes": 0.0
  },
  "metadata": {
    "analyzedAt": "2026-01-28T15:30:00.000000",
    "textPreview": "Serverless computing is amazing. It scales automatically."
  }
}
```

> **Note:** This is the same Text Analyzer code from Week 2. The inline comments explain each section in detail.

---

## Part 7: Sign in to Azure

Before deploying, you must authenticate with Azure.

### Steps:

1. Click the **Azure icon** in the Activity bar

2. Under **Resources**, click **Sign in to Azure...**

3. When prompted in the browser, sign in with your Azure account credentials

4. After signing in, close the browser window

5. Your subscriptions will appear in the VS Code sidebar

---

## Part 8: Create a Function App in Azure

Now you'll create the cloud resources to host your function.

### Step 8.1: Create the Function App

1. Press `F1` to open the Command Palette

2. Search for and select: **Azure Functions: Create Function App in Azure...(Advanced)**

### Step 8.2: Configure the Function App

The Advanced option gives you more control over the resources being created. Provide the following information at each prompt:

| Prompt                                      | Your Action                                                      |
| ------------------------------------------- | ---------------------------------------------------------------- |
| **Select subscription**                     | Choose your Azure subscription                                   |
| **Enter a globally unique name**            | Enter a unique name (e.g., `yourname-func-lab1`)                 |
| **Select a runtime stack**                  | `Python 3.12`                                                    |
| **Select an OS**                            | `Linux`                                                          |
| **Select a resource group**                 | Create new or select existing (e.g., `rg-serverless-lab1`)       |
| **Select a location**                       | Choose a region near you (e.g., `Canada Central`)                |
| **Select a hosting plan**                   | `Consumption`                                                    |
| **Select a storage account**                | Create new (e.g., `stserverlesslab1yourname`) or select existing |
| **Select an Application Insights resource** | `Skip for now`                                                   |
| **Select resource authentication type**     | `Secrets` (simpler setup for lab purposes)                       |

### Step 8.3: Monitor Creation Progress

Watch the **Azure: Activity Log** panel to see resources being created:

- **Resource group** - Container for related resources
- **Function app** - Environment for your function code
- **App Service plan** - Defines the hosting plan
- **Storage account** - Maintains state and function information
- **Application Insights** - Tracks function usage and performance
- **Managed identity** - Secure authentication for Azure services

A notification appears when creation is complete.

---

## Part 9: Deploy to Azure

### Step 9.1: Deploy Your Code

#### Option A: Using VS Code

1. Press `F1` to open the Command Palette

2. Search for and select: **Azure Functions: Deploy to Function App**

3. Select the function app you just created

4. When prompted about overwriting, select **Deploy**

#### Option B: Using the Command Line

```bash
func azure functionapp publish <your-function-app-name>
```

Replace `<your-function-app-name>` with the name you chose in Step 8.2 (e.g., `yourname-func-lab1`).

Example:
```bash
func azure functionapp publish yourname-func-lab1
```

> **Note:** Make sure you're logged into Azure CLI (`az login`) before running this command.

### Step 9.2: Verify Deployment

1. When deployment completes, click **View Output** in the notification

2. Review the deployment results and created resources

> **Tip:** If you miss the notification, click the bell icon in the lower-right corner.

### Troubleshooting: Functions Not Showing After Deployment

> **Note:** If you selected **Secrets** as the authentication type in Step 8.2, you should not encounter this issue. This section applies if you chose **Managed identity** instead.

If your deployment succeeds but you don't see your functions listed under the Function App in Azure Portal or VS Code, this is likely due to the managed identity not having the required permissions to access the storage account.

**Fix: Assign Storage Blob Data Contributor Role**

1. In the Azure Portal, navigate to your **Storage Account** (the one created with your function app)

2. In the left menu, click **Access Control (IAM)**

3. Click **+ Add** > **Add role assignment**

4. Select role: **Storage Blob Data Contributor**

5. Click **Next**, then select **Managed identity**

6. Click **+ Select members**

7. Find and select your **Function App's managed identity** (it has the same name as your function app)

8. Click **Select**, then **Review + assign**

9. Wait a few minutes, then refresh your Function App in the portal

---

## Part 10: Test Your Deployed Function

### Step 10.1: Execute in Azure

1. Press `F1` and run: **Azure Functions: Execute Function Now...**

2. Select your subscription (if prompted)

3. Select your function app, then select `TextAnalyzer`

4. Enter the request body:
   ```json
   { "text": "Serverless computing is amazing. It scales automatically." }
   ```

5. Press **Enter** to send the request

6. View the response in the notification area

### Step 10.2: Verify Success

Expand the notification to see the full response from your cloud-deployed function. You should see the text analysis results including word count, character count, sentence count, and more.

---

# Part 2: Persist Analysis Results to Azure Database

In Part 1, you built and deployed a Text Analyzer function. Now you'll extend it by storing analysis results in an Azure database. This part requires you to **research, evaluate, and implement** a database solution independently.

---

## Part 11: Research Azure Database Options

Before writing any code, you need to choose the right database for storing your Text Analyzer results.

### Step 11.1: Investigate Azure Database Services

Research the following Azure database options and evaluate their suitability for storing JSON analysis results:

| Database Service        | Research Questions to Answer                                           |
| ----------------------- | ---------------------------------------------------------------------- |
| **Azure Cosmos DB**     | What is it? What data models does it support? What is serverless tier? |
| **Azure Table Storage** | What is it? How does it differ from Cosmos DB? When is it appropriate? |
| **Azure SQL Database**  | What is it? When would you choose SQL over NoSQL?                      |
| **Azure Blob Storage**  | Can it be used as a database? What are the trade-offs?                 |

### Step 11.2: Evaluate and Choose

Consider the following criteria when making your decision:

| Criteria               | Questions to Consider                                                      |
| ---------------------- | -------------------------------------------------------------------------- |
| **Data Structure**     | Your analysis results are JSON. Which database handles JSON naturally?     |
| **Cost**               | Which options have free tiers or serverless pricing suitable for students? |
| **Complexity**         | How much setup is required? Do you need to define schemas?                 |
| **Scalability**        | Does it align with serverless principles?                                  |
| **Python SDK**         | Is there good Python support for Azure Functions integration?              |
| **Query Capabilities** | Do you need to query historical results? How complex are your queries?     |

### Step 11.3: Document Your Decision

Create a file named `DATABASE_CHOICE.md` in your project root with:

1. **Your Choice**: Which database did you select?
2. **Justification**: Why is this the best choice for this use case? (3-5 sentences)
3. **Alternatives Considered**: What other options did you evaluate and why did you reject them?
4. **Cost Considerations**: How does pricing work for your chosen database?

> **Hint:** For storing JSON documents from a serverless function with minimal cost, one option stands out as particularly well-suited. Research "Azure Cosmos DB serverless" and "Azure Cosmos DB free tier."

---

## Part 12: Create Your Database in Azure

Based on your research, create the database resource in Azure.

### Step 12.1: Create the Database Resource

Use the **Azure Portal** to create your chosen database:

1. Navigate to [portal.azure.com](https://portal.azure.com)
2. Click **+ Create a resource**
3. Search for your chosen database service
4. Configure the resource with appropriate settings for a development/learning scenario

> **Important:** Use the same resource group you created in Part 1 (`rg-serverless-lab1`) to keep all lab resources together.

### Step 12.2: Note Your Connection Details

After creation, locate and save the following (you'll need these for your function):

- **Endpoint/Connection String**: How your function connects to the database
- **Database Name**: The name of your database
- **Container/Table/Collection Name**: Where your data will be stored

> **Security Reminder:** Never commit connection strings to source control. You'll add these to `local.settings.json` (which is gitignored) for local development, and to Azure Application Settings for production.

---

## Part 13: Modify Your Function to Store Results

Now extend your Text Analyzer function to save results to your database.

### Step 13.1: Update Dependencies

Add any required Python packages to your `requirements.txt` file. Research which SDK package is needed for your chosen database.

### Step 13.2: Add Connection String to Local Settings

Update your `local.settings.json` to include the database connection string:

```json
{
  "IsEncrypted": false,
  "Values": {
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "DATABASE_CONNECTION_STRING": "your-connection-string-here"
  }
}
```

> **Note:** The setting name may vary depending on your database choice. Research the recommended environment variable names for your chosen database.

### Step 13.3: Modify function_app.py

Update your function code to:

1. **Import** the appropriate database SDK
2. **Connect** to your database using the connection string from environment variables
3. **Store** each analysis result with a unique identifier
4. **Return** the analysis result (as before) plus the ID of the stored record

Your stored document should include:

| Field          | Description                              |
| -------------- | ---------------------------------------- |
| `id`           | Unique identifier for this analysis      |
| `analysis`     | The analysis results (word count, etc.)  |
| `metadata`     | Timestamp and text preview               |
| `originalText` | The full original text that was analyzed |

> **Hint:** Use Python's `uuid` module to generate unique IDs: `import uuid` then `str(uuid.uuid4())`

### Step 13.4: Test Locally

1. Start Azurite (`F1` > **Azurite: Start**)
2. Run your function (`F5` or `func start`)
3. Send a test request to analyze some text
4. Verify in Azure Portal that the data was stored in your database

---

## Part 14: Add a History Endpoint

Create a second function endpoint that retrieves past analysis results.

### Step 14.1: Create GetAnalysisHistory Function

Add a new function to `function_app.py` that:

1. Connects to your database
2. Retrieves stored analysis records
3. Returns them as a JSON array

**Endpoint Requirements:**

| Aspect              | Requirement                                                            |
| ------------------- | ---------------------------------------------------------------------- |
| **Route**           | `/api/GetAnalysisHistory`                                              |
| **Method**          | GET                                                                    |
| **Query Parameter** | `limit` (optional) - maximum number of results to return (default: 10) |
| **Response**        | JSON array of past analysis results                                    |

**Example Response:**
```json
{
  "count": 2,
  "results": [
    {
      "id": "abc123-...",
      "analysis": { "wordCount": 7, ... },
      "metadata": { "analyzedAt": "2026-01-28T15:30:00", ... }
    },
    {
      "id": "def456-...",
      "analysis": { "wordCount": 12, ... },
      "metadata": { "analyzedAt": "2026-01-28T14:20:00", ... }
    }
  ]
}
```

### Step 14.2: Test the History Endpoint

1. Run several text analyses to populate your database
2. Call the history endpoint: `http://localhost:7071/api/GetAnalysisHistory`
3. Verify you receive the stored results
4. Test the `limit` parameter: `http://localhost:7071/api/GetAnalysisHistory?limit=5`

---

## Part 15: Deploy and Configure in Azure

### Step 15.1: Add Connection String to Azure

Your deployed function needs access to the database connection string:

1. In Azure Portal, navigate to your **Function App**
2. Go to **Settings** > **Environment variables** (or **Configuration** > **Application settings**)
3. Click **+ Add**
4. Add your database connection string with the same name used in `local.settings.json`
5. Click **Save** and confirm the restart

### Step 15.2: Deploy Updated Function

Deploy your updated code to Azure:

**Using VS Code:**
1. Press `F1` > **Azure Functions: Deploy to Function App**
2. Select your function app
3. Confirm the deployment

**Using CLI:**
```bash
func azure functionapp publish <your-function-app-name>
```

### Step 15.3: Verify in Azure

1. Test the `TextAnalyzer` endpoint in Azure - verify results are stored
2. Test the `GetAnalysisHistory` endpoint - verify you can retrieve stored results
3. Check your database in Azure Portal to confirm data is being saved

---

## Part 16: Submission

### Deliverables

Submit your completed lab by providing a **GitHub repository URL** containing:

| Item                       | Description                                                                                 |
| -------------------------- | ------------------------------------------------------------------------------------------- |
| **Function Code**          | Your complete `function_app.py` with both `TextAnalyzer` and `GetAnalysisHistory` functions |
| **Requirements**           | Updated `requirements.txt` with database SDK dependencies                                   |
| **Database Documentation** | `DATABASE_CHOICE.md` explaining your database selection and justification                   |
| **Demo Video Link**        | `DEMO.md` YouTube link to your demonstration video                                          |
| **README**                 | Brief instructions on how to run your project locally (environment variables needed, etc.)  |

### Demo Video Requirements

Record a demonstration video (maximum 5 minutes) showing your working project:

| Requirement  | Details                                    |
| ------------ | ------------------------------------------ |
| **Duration** | Maximum 5 minutes                          |
| **Audio**    | Not required (no narration needed)         |
| **Platform** | Upload to YouTube (unlisted is fine)       |
| **Link**     | Include the YouTube URL in your repository |

### Submission Format

Submit only your **GitHub repository URL** to Brightspace.
