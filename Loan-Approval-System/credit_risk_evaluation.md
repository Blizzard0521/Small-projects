# 🏦 Credit Risk Scoring: Bridging Machine Learning with Business Value

## 📖 The Journey & Context
This project started as a standard university assignment on classification models (Decision Trees vs. Random Forests) using the German Credit Risk dataset. Initially, I approached it purely from a technical standpoint: train the models, look at Accuracy, print the ROC-AUC, and pick the highest number. 

However, as I dug deeper, I realized that in the real world of consumer banking, **accuracy is not enough**. A model can be 90% accurate but still bankrupt a company if its errors are asymmetrical. This project became a deep dive into translating technical Python outputs into strategic business KPIs. 

## 🧠 What I Learned (My "Aha!" Moments)

### 1. Not All Errors Are Created Equal
I learned to assign real-world financial weights to the confusion matrix:
* **The $10,000 Mistake (False Positive):** The model predicts a customer is "Good" (1), but they are actually "Bad" (0). The bank lends the money, the customer defaults, and the principal is lost. 
* **The $500 Mistake (False Negative):** The model predicts "Bad" (0), but the customer is "Good" (1). The bank rejects a valid loan, losing out on interest revenue.

### 2. The Danger of Mislabeling Variables in `sklearn`
One of the biggest technical roadblocks I faced was mapping the `sklearn` confusion matrix to my business logic. Because my target was encoded as `1 = Good` and `0 = Bad`, the standard `sklearn` output `[0, 1]` represented *Actual Bad, Predicted Good*. 
* Originally, I mislabeled this as a False Negative in my code. While the math accidentally worked out because I also swapped the cost multipliers, I realized that **semantic variable naming is critical**. Calling a default a "False Negative" would completely confuse a future developer or stakeholder reading my code. I refactored the KPI engine to use clear business terms (`COST_DEFAULT` and `COST_REJECTION`).

### 3. Safety vs. Growth
When evaluating the final models, I found something fascinating:
* Both the Decision Tree and the Random Forest caught the exact same number of defaults (26). Their **Risk Exposure** was identical.
* However, the Random Forest was much better at recognizing good customers. It rejected 10 fewer valid applicants. 
* **The Takeaway:** The Random Forest wasn't chosen because it was "safer." It was chosen because it drove **Growth**. It safely increased the approval rate by 5%, generating an additional $5,000 in Net Monetary Benefit without taking on extra bad debt.

## 🛠️ Technical Skills Demonstrated
* **Python & Scikit-Learn:** Building, training, and extracting metrics from Decision Trees and Random Forests.
* **Metric Extraction:** Unpacking `confusion_matrix.ravel()` and mapping indices dynamically to business logic.
* **Financial Modeling in Code:** Building a custom evaluation script that calculates Baseline Loss, Risk Exposure (Leakage), Approval Rate, and Net Monetary Benefit (ROI).

## 🚀 Key Takeaways for Interviews
If an interviewer asks me about this project, my main talking points are:
1. **Model selection must align with business constraints.** I didn't just pick Random Forest because of a higher AUC (0.71 vs 0.67); I picked it because it mathematically proved a higher Net Monetary Benefit.
2. **Translating Data Science to Stakeholders.** I learned how to reframe a "False Negative" into an "Opportunity Cost" and a "False Positive" into "Capital Erosion" so that business leaders can understand the model's value.
3. **Attention to detail in code readability.** Ensuring that variable names reflect the true state of the data (e.g., using `fp_defaults` instead of generic index slicing) to prevent downstream logical errors.

## ⚙️ How to Run the Code
1. Clone this repository.
2. Ensure you have the German Credit Dataset (`credit_df` formatted with `1=Good`, `0=Bad`).
3. Run `credit_risk_evaluation.py` to see the custom Business KPI Engine print the financial analysis to the console.