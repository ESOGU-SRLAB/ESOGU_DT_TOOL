import streamlit as st
from pydantic import BaseModel
from typing import List, Optional
import json
from datetime import datetime
import uuid
from pymongo import MongoClient
import os
from ollama import chat
import streamlit_mermaid as stmd

##############################
# 1) MongoDB'den Veri Çekme #
##############################

MONGO_URI = os.getenv("MONGO_URI")  # Ortam değişkeninden URI al
client = MongoClient(MONGO_URI)
db = client["modular_test_scenario_gen"]
collection = db["sessions"]

# Mevcut sonuçları kontrol et ve getir (varsa) - MongoDB'den
def check_existing_results(process_title, selected_category, selected_test_type):
    """
    MongoDB'de belirli bir (process_title, selected_category, selected_test_type) ve smart_selection_results alanı var mı kontrol eder.
    """
    existing_entry = collection.find_one(
        {
            "process_title": process_title,
            "selected_category": selected_category,
            "selected_test_type": selected_test_type
        },
        {
            "smart_selection_results": 1
        }
    )
    return existing_entry.get("smart_selection_results") if existing_entry else None

def save_smart_selection_results(process_title, selected_category, selected_test_type, results):
    """
    MongoDB'ye (process_title, selected_category, selected_test_type) ve smart_selection_results alanına sonuçları kaydeder.
    """
    collection.update_one(
        {
            "process_title": process_title,
            "selected_category": selected_category,
            "selected_test_type": selected_test_type
        },
        {
            "$set": {
                "smart_selection_results": results
            }
        },
        upsert = True # Eğer yoksa yeni bir kayıt oluştur, varsa güncelle
    )

def fetch_valid_combinations():
    """
    MongoDB'den benzersiz (process_title, selected_category, selected_test_type) 
    kombinasyonlarını getirir. Null değerleri filtreler, ancak boş string değerleri kabul eder.
    """
    data = collection.find(
        {}, 
        {"process_title": 1, "selected_category": 1, "selected_test_type": 1}
    )
    combinations = [
        {
            "process_title": entry.get("process_title"),
            "selected_category": entry.get("selected_category"),
            "selected_test_type": entry.get("selected_test_type")
        }
        for entry in data
        if entry.get("process_title") is not None 
           and entry.get("selected_category") is not None 
           and entry.get("selected_test_type") is not None
    ]
    return combinations

def fetch_details_by_combination(process_title, selected_category, selected_test_type):
    """
    Seçilen (process_title, selected_category, selected_test_type) kombinasyonuna göre detayları getirir.
    Title, Description veya Objective değeri None olmayan test case'leri döndürür.
    """
    data = collection.find_one(
        {
            "process_title": process_title,
            "selected_category": selected_category,
            "selected_test_type": selected_test_type
        },
        {
            "process_title": 1,
            "selected_category": 1,
            "selected_test_type": 1,
            "model_output.TestCases": 1
        }
    )
    
    if not data:
        return None

    # Test case'leri al
    valid_test_cases = []
    test_cases = data.get("model_output", {}).get("TestCases", [])

    for case_group in test_cases:
        scenario_id = case_group.get("scenario_id", "Unknown Scenario")

        # Test case'leri al (None kontrolü artık gereksiz)
        # get() zaten None döndürmediği için fazladan kontrol yapılmasına gerek yok.
        test_case_data = case_group.get("test_case", [])

        # Eğer `test_case_data` bir listeyse direkt kullan
        if isinstance(test_case_data, list):
            tcases = test_case_data
        elif isinstance(test_case_data, dict):
            tcases = test_case_data.get("TestCases", [])
        else:
            tcases = []

        # **Python tarafında ekstra filtrelemeye gerek yok çünkü MongoDB sorgusu zaten None değerleri filtreledi.**
        if tcases:
            valid_test_cases.append({
                "scenario_id": scenario_id,
                "test_case": tcases
            })

    # Eğer hiçbir geçerli test case yoksa None döndür
    if not valid_test_cases:
        return None

    # Model output içinde geçerli test case'leri güncelle
    data["model_output"]["TestCases"] = valid_test_cases
    return data



##############################################
# 2) TestCase ve Smart Selection Sınıfları  #
##############################################

class TestCase(BaseModel):
    ScenarioID: str
    TestCaseID: str
    Title: str
    Description: Optional[str] = None
    Objective: Optional[str] = None

class TestCaseList(BaseModel):
    test_cases: List[TestCase]
    comparison_logs: List[dict] = []
    duplicates: List[dict] = []  # Benzer test durumlarını saklamak için yeni bir liste

    def smart_select(self):
        """
        Bu metot, test_cases listesindeki benzer (duplicate) test case'leri 
        LLM tabanlı karşılaştırma ile ayıklar, unique bir liste döndürür.
        """
        unique_cases = []
        step = 1

        for case in self.test_cases:
            is_duplicate = False
            for unique_case in unique_cases:
                try:
                    comparison_result = self._query_llm_similarity(case, unique_case)
                except ValueError as e:
                    # LLM cevabı geçersiz ya da hata varsa false kabul ediyoruz
                    st.warning(f"LLM comparison failed: {e}")
                    comparison_result = False

                self.comparison_logs.append({
                    "Step": step,
                    "ProcessName": str(uuid.uuid4()),
                    "Timestamp": datetime.now().isoformat(),
                    "Case1": case.model_dump(),
                    "Case2": unique_case.model_dump(),
                    "is_same": comparison_result,
                })
                step += 1
                if comparison_result:
                    is_duplicate = True
                    # Benzer test durumlarını kaydet
                    self.duplicates.append({
                        "DuplicateCase": case.model_dump(),
                        "MatchedWith": unique_case.model_dump()
                    })
                    break

            if not is_duplicate:
                unique_cases.append(case)

        return TestCaseList(
            test_cases=unique_cases,
            comparison_logs=self.comparison_logs,
            duplicates=self.duplicates
        )

    @staticmethod
    def _query_llm_similarity(case1: "TestCase", case2: "TestCase") -> bool:
        """
        İki TestCase nesnesini LLM'e JSON formatında göndererek benzerlik (is_same) sonucunu döndürür.
        """

        # Create JSON objects
        case1_json = case1.model_dump()
        case2_json = case2.model_dump()

        # Pop the ScenarioID and TestCaseID keys
        case1_json.pop("ScenarioID", None)
        case1_json.pop("TestCaseID", None)

        case2_json.pop("ScenarioID", None)
        case2_json.pop("TestCaseID", None)

        # Prompt text for Smart Selection using LLM
        prompt_text = f"""
You are given two test cases, each with a certain set of fields:
- Title
- Description
- Objective

You will decide whether these two test cases are “contextually the same” based on the following criteria:

1. If both have the same Title (case-insensitive) OR their Titles are substantially similar in meaning,
2. AND they have either the same or very similar Description and/or Objective,
3. AND they serve essentially the same testing purpose for the same or very closely related scenarios,
4. THEN you should conclude that these two test cases are the same.
5. The order of importance Description > Objective > Title.

Otherwise, they are considered different.

Below are the two test cases in JSON format:

TestCase1:
{json.dumps(case1_json, indent=2, ensure_ascii=False)}

TestCase2:
{json.dumps(case2_json, indent=2, ensure_ascii=False)}

Return your response **only** in valid JSON with the following format:

{{
  "is_same": <true or false>
}}

Where:
- is_same = true if the test cases meet the criteria above
- is_same = false otherwise

Important:
- Do not provide any additional text outside the JSON object.
- Do not explain your reasoning, only provide the final JSON response.
"""
        print(prompt_text)
        # Ollama üzerinden LLM'e istek
        messages = [
            {
                "role": "user",
                "content": prompt_text.strip()
            }
        ]

        response = chat(
            messages=messages,
            model='llama3.2',  # Örnek model ismi
            format={
                "type": "object",
                "properties": {
                    "is_same": {"type": "boolean"}
                },
                "required": ["is_same"]
            },
        )

        content = response.get('message', {}).get('content', '').strip()
        try:
            parsed_content = json.loads(content)
            return parsed_content.get("is_same", False)
        except json.JSONDecodeError:
            raise ValueError(f"LLM response is not valid JSON: {content}")


###################################
# 3) Streamlit Arayüz ve Mantık  #
###################################

def main():
    st.set_page_config(
        page_title="Smart Selection",
        layout="wide"
    )

    st.title("Fetch Data and Smart Selection")

    with st.expander("Workflow Steps", expanded=False):
        st.markdown("""
        ### 1. Fetch Valid Combinations
        - Query MongoDB for combinations of `process_title`, `selected_category`, and `selected_test_type`.
        - Filter out combinations with null values.

        ### 2. Select a Combination
        - Users are prompted to select a combination from the available options.
        - If no combinations are found, the message **'No Valid Combinations Found'** is displayed.

        ### 3. Fetch Test Case Details
        - Retrieve the test case details for the selected combination.
        - If no details are found, the message **'No Details Found'** is displayed.

        ### 4. Test Case Selection
        - Display the list of test cases for the user to review and select.
        - Provide **Select All** and **Deselect All** buttons for bulk selection.

        ### 5. Smart Selection
        - Once the user selects test cases, the **Smart Selection** process begins:
            1. Test cases are compared using an LLM-based similarity check.
            2. Similar test cases are added to the **Similar Cases** list.
            3. Unique test cases are added to the **Unique Cases** list.

        ### 6. Display Results
        - After the process is completed, the following results are displayed:
            - Unique test cases.
            - Similar test cases.
            - All comparison logs.

        ### 7. Download Results
        - Allow the user to download results in JSON format:
            - **Unique Test Cases**
            - **All Test Cases**
        """)

#     diagram = """
# flowchart TB
#     A("Start") --> B["Fetch Valid Combinations from MongoDB"]
#     B --> C{"Are Combinations Available?"}
#     C -- "No" --> D["Display 'No Valid Combinations Found'"]
#     C -- "Yes" --> E["Select Combination:<br/> Process Title - Test Type - Category"]
#     E --> F{"Details Available for Combination?"}
#     F -- "No" --> G["Display 'No Details Found'"]
#     F -- "Yes" --> H["Fetch Test Cases for Selected Combination"]
#     H --> I{"Are Test Cases Available?"}
#     I -- "No" --> J["Display 'No Test Cases Found'"]
#     I -- "Yes" --> K["Display Test Cases with Select Options"]
#     K --> L["Select/Deselect All Test Cases Option"]
#     L --> M["Display Selected Test Cases"]
#     M --> N{"Run Smart Selection?"}
#     N -- "No" --> O["Wait for User Action"]
#     N -- "Yes" --> P["Validate and Convert Selected Test Cases to Objects"]
#     P --> Q{"Are Valid Test Cases Available?"}
#     Q -- "No" --> R["Display 'No Valid Test Cases'"]
#     Q -- "Yes" --> S["Process Smart Selection Using LLM"]
#     S --> T["Log Results:<br/> Unique Cases, Similar Cases, and Comparison Logs"]
#     T --> U["Display Results:<br/> Unique Cases, Similar Cases, Logs"]
#     U --> V["Provide Download Options for Results"]
#     V --> W("End")
# """
#     stmd.st_mermaid(diagram)

    # Session state kontrolü
    if "selected_test_cases" not in st.session_state:
        st.session_state.selected_test_cases = {}

    if "all_cases_keys" not in st.session_state:
        st.session_state.all_cases_keys = []

    if "fetched_test_cases" not in st.session_state:
        st.session_state.fetched_test_cases = []

    # 1) Veritabanından geçerli kombinasyonları çek
    combinations = fetch_valid_combinations()

    if combinations:
        # Selectbox için mevcut kombinasyonları hazırla
        options = [
            f"{entry['process_title']} - {entry['selected_test_type']} - {entry['selected_category']}"
            for entry in combinations
        ]
        # Varsayılan seçenek
        options.insert(0, "Select a Process Title - Test Type - Category")

        selected_option = st.selectbox("Select a Process Title - Test Type - Category:", options)

        # Eğer varsayılan seçenek seçilmişse hiçbir işlem yapılmaz
        if selected_option != "Select a Process Title - Test Type - Category":
            # Seçilen kombinasyonun detaylarını getirme
            selected_index = options.index(selected_option) - 1  # Varsayılanı hesaba kat
            selected_entry = combinations[selected_index]

            process_title = selected_entry["process_title"]
            selected_category = selected_entry["selected_category"]
            selected_test_type = selected_entry["selected_test_type"]

            # Detayları getir ve göster
            details = fetch_details_by_combination(process_title, selected_category, selected_test_type)

            if details:
                existing_results = check_existing_results(process_title, selected_category, selected_test_type)
                if existing_results:
                    st.warning("Smart Selection results already exist for this combination in database!")

                st.subheader(f"Details for: {details['process_title']}")
                st.write(f"- **Selected Category**: {details['selected_category']}")
                st.write(f"- **Selected Test Type**: {details['selected_test_type']}")

                # TestCases bilgilerini getir
                test_cases = details.get("model_output", {}).get("TestCases", [])

                if test_cases:
                    st.write("### Test Cases")

                    # Seçilen test vaka anahtarlarını sıfırla
                    st.session_state.all_cases_keys = []
                    st.session_state.fetched_test_cases = []  # Seçimler için tüm test case'leri hafızaya alalım

                    for case_group in test_cases:
                        scenario_id = case_group.get("scenario_id", "Unknown Scenario")
                        st.write(f"#### Scenario: {scenario_id}")

                        # tcases = case_group.get("test_case", {}).get("TestCases", [])

                        test_case_data = case_group.get("test_case", [])

                        # Eğer `None` gelirse, bunu boş listeye çevir
                        if test_case_data is None:
                            test_case_data = []

                        if isinstance(test_case_data, list):
                            tcases = test_case_data
                        elif isinstance(test_case_data, dict):
                            tcases = test_case_data.get("TestCases", [])
                        else:
                            tcases = []

                        if tcases:
                            for idx, c in enumerate(tcases):
                                case_id = c.get("TestCaseID", f"Unknown_ID_{idx}")
                                title = c.get("Title", "No Title")
                                description = c.get("Description", "No Description")
                                objective = c.get("Objective", "No Objective")
                                category = c.get("Category", "No Category")
                                comments = c.get("Comments", "No Comments")

                                # Benzersiz anahtar
                                unique_key = f"{scenario_id}_{case_id}"

                                # Eğer session_state'te yoksa başlangıçta False set et
                                if unique_key not in st.session_state.selected_test_cases:
                                    st.session_state.selected_test_cases[unique_key] = False

                                # Checkbox
                                selected = st.checkbox(
                                    f"{case_id}: {title}",
                                    key=unique_key,
                                    value=st.session_state.selected_test_cases[unique_key]
                                )
                                # Seçim durumunu güncelle
                                st.session_state.selected_test_cases[unique_key] = selected

                                # Tüm anahtarları listede tut
                                st.session_state.all_cases_keys.append(unique_key)

                                # Test case detaylarını yaz
                                st.write(f"- **Scenario**: {scenario_id}")
                                st.write(f"- **Test Case**: {case_id}")
                                st.write(f"- **Title**: {title}")
                                st.write(f"- **Description**: {description}")
                                st.write(f"- **Objective**: {objective}")
                                st.write(f"- **Category**: {category}")
                                st.write(f"- **Comments**: {comments}")
                                st.write("---")

                                # İleride Smart Selection'da kullanmak için dictionary olarak tutuyoruz
                                st.session_state.fetched_test_cases.append({
                                    "ScenarioID": scenario_id,
                                    "TestCaseID": case_id,
                                    "Title": title,
                                    "Description": description,
                                    "Objective": objective
                                })

                        else:
                            st.write("No Test Cases Found for this Scenario.")

                    # Tümünü seç / Kaldır butonları
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Select All Test Cases"):
                            for key in st.session_state.all_cases_keys:
                                st.session_state.selected_test_cases[key] = True
                    with col2:
                        if st.button("Deselect All Test Cases"):
                            for key in st.session_state.all_cases_keys:
                                st.session_state.selected_test_cases[key] = False

                    st.write("---")

                    # Seçilen test case'leri göster
                    if st.button("Save and Show Selected Test Cases"):
                        selected_cases = []
                        for case_dict in st.session_state.fetched_test_cases:
                            # Unique key'i tekrar oluştur: ScenarioID + TestCaseID
                            unique_key = f"{case_dict['ScenarioID']}_{case_dict['TestCaseID']}"
                            if st.session_state.selected_test_cases.get(unique_key, False):
                                selected_cases.append(case_dict)

                        if selected_cases:
                            with st.expander("### Selected Test Cases (JSON)", expanded=False):
                                st.json(selected_cases)
                        else:
                            st.warning("No test cases selected.")

                else:
                    st.write("No Test Cases Found for this Scenario.")
            else:
                st.write("No details found for the selected combination.")
    else:
        st.write("No valid combinations found in the database.")


    ###############################################
    # 4) Smart Selection Butonu ve Sonuçların Gösterimi
    ###############################################
    st.write("---")
    st.write("## Smart Selection")
    st.write("Smart selection process will compare the selected test cases using an LLM-based similarity check.")

    if st.button("Run Smart Selection"):
        selected_cases = []
        for case_dict in st.session_state.fetched_test_cases:
            unique_key = f"{case_dict['ScenarioID']}_{case_dict['TestCaseID']}"
            if st.session_state.selected_test_cases.get(unique_key, False):
                selected_cases.append(case_dict)

        if not selected_cases:
            st.warning("No test cases selected for Smart Selection!")
        else:
            # Pydantic modeline dönüştür
            valid_data = []
            for item in selected_cases:
                try:
                    valid_data.append(TestCase(**item))
                except Exception as e:
                    st.warning(f"Skipping invalid test case: {item}. Error: {e}")

            if valid_data:
                test_case_list = TestCaseList(test_cases=valid_data)
                unique_test_cases = test_case_list.smart_select()

                st.success("Smart Selection completed!")

                results = {
                    "unique_test_cases": [case.model_dump() for case in unique_test_cases.test_cases],
                    "similar_test_cases": unique_test_cases.duplicates,
                    "comparison_logs": unique_test_cases.comparison_logs,
                }
                
                # Benzersiz test case'ler
                with st.expander("Unique Test Cases", expanded=False):
                    st.json([case.model_dump() for case in unique_test_cases.test_cases])

                # Benzer test case'ler
                if unique_test_cases.duplicates:
                    st.warning("Similar test cases were found!")
                    with st.expander("Similar Test Cases", expanded=False):
                        st.json(unique_test_cases.duplicates)

                # Karşılaştırma logları
                st.info("All comparison logs are here!", icon="ℹ️")
                with st.expander("Comparison Logs", expanded=False):
                    st.json(unique_test_cases.comparison_logs)

                # Download sonuçları
                results = {
                    "unique_test_cases": [case.model_dump() for case in unique_test_cases.test_cases],
                    "similar_test_cases": unique_test_cases.duplicates,
                    "comparison_logs": unique_test_cases.comparison_logs
                }

                # MongoDB'ye sonuçları kaydet
                save_smart_selection_results(process_title, selected_category, selected_test_type, results)
                st.success("Smart Selection results saved to MongoDB!")


                # st.download_button(
                #     label="Download Unique Test Cases",
                #     data=json.dumps(results, indent=2),
                #     file_name="unique_test_cases.json",
                #     mime="application/json"
                # )

                # st.download_button(
                #     label="Download Smart Selection Results",
                #     data=json.dumps(results, indent=2),
                #     file_name="smart_selection_results.json",
                #     mime="application/json"
                # )

                col1_unique, col2_all = st.columns(2)

                # İlk sütunda "Download Unique Test Cases" butonu
                with col1_unique:
                    if st.download_button(
                        label="Download Unique Test Cases",
                        data=json.dumps(results, indent=2),
                        file_name="unique_test_cases.json",
                        mime="application/json"
                    ):
                        st.success("Unique test cases downloaded!")  # İsteğe bağlı bir başarı mesajı

                # İkinci sütunda "Download All Test Cases" butonu
                with col2_all:
                    if st.download_button(
                        label="Download All Test Cases",
                        data=json.dumps(results, indent=2),
                        file_name="all_test_cases.json",
                        mime="application/json"
                    ):
                        st.success("All test cases downloaded!")  # İsteğe bağlı bir başarı mesajı
            else:
                st.error("No valid TestCase objects to process.")


if __name__ == "__main__":
    main()
