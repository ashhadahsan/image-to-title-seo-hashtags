from clip_interrogator import Config, Interrogator
from langchain.chat_models import ChatOpenAI
from langchain import LLMChain
from functools import lru_cache
from langchain.prompts.chat import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
import os

os.environ["OPENAI_API_KEY"] = "KEY"
os.environ["REPLICATE_API_TOKEN"] = "KEY"
caption_model_name = (
    "blip-large"  # @param ["blip-base", "blip-large", "git-large-coco"]
)
clip_model_name = (
    "ViT-L-14/openai"  # @param ["ViT-L-14/openai", "ViT-H-14/laion2b_s32b_b79k"]
)


@lru_cache(maxsize=None)
def load_model():
    config = Config()
    config.clip_model_name = clip_model_name
    config.caption_model_name = caption_model_name
    config.caption_max_length = 20
    # config.download_cache = False

    ci = Interrogator(config)
    return ci


# ci = load_model()


# def image_to_prompt(image, mode):
#     ci.config.chunk_size = (
#         2048 if ci.config.clip_model_name == "ViT-L-14/openai" else 1024
#     )
#     ci.config.flavor_intermediate_count = (
#         2048 if ci.config.clip_model_name == "ViT-L-14/openai" else 1024
#     )
#     image = image.convert("RGB")
#     if mode == "best":
#         return ci.interrogate(image)
#     elif mode == "classic":
#         return ci.interrogate_classic(image)
#     elif mode == "fast":
#         return ci.interrogate_fast(image, max_flavors=4)
#     elif mode == "negative":
#         return ci.interrogate_negative(image)
import replicate


def image_to_prompt(image, model: str = "best"):
    output = replicate.run(
        "pharmapsychotic/clip-interrogator:a4a8bafd6089e1716b06057c42b19378250d008b80fe87caa5cd36d40c1eda90",
        input={"image": open(image, "rb"), "mode": model},
    )
    return output


def get_title_desc_seo(
    style_input: str,
    text_input: str,
    hashtags_len: int,
    length_of_title: str,
    length_of_description: str,
    brand_name: str,
    product_style: str,
):
    # system_template = "You are a helpful assistant that writes title in {title_length} words, detailed and concise description in {description_length} words and {number} seo hashtgs in a {style} way from keywords. The output keys are Title, Description, Hashtags "
    system_template = """Please ignore all previous instructions. I want you to act as a very proficient SEO for the {brand} and high-end eCommerce copywriter that speaks and writes fluently English about the {style_product} of the product in a {style} manner*. Write a {description_length} word product description in English* based on the product details I give you. From this input description, you will write an engaging short Title in {title_length}, Description and finish with {number} SEO hashtags that are on the same line (if the description mentions gender add them into tags). never mention any artists, or inspired artists or photographers - keep it vague in that way.
    Please ensure that the generated output does not reference any inspiration derived from a specific artist, avoids mentioning the names of artists, and abstains from attributing the work to a particular individual. This approach will help maintain the focus on the artwork itself while preventing potential attribution or copyright concerns.

Also, follow these guidelines:
- Focus on benefits rather than features
- Avoid sentences over 20 words
- Avoid using passive voice
- Include a call to action at the end (be unique each one)
- Make each description unique from each other.
- Never mention inspired by artists or photographers, etc.
- never mention CG society or anything similar
- never say as featured or anything similar to that
- Include the brand name in the description if necessary
The output keys are Title, Description, Hashtags
"""

    system_message_prompt = SystemMessagePromptTemplate.from_template(system_template)
    human_template = "{text}"
    human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)
    chat = ChatOpenAI(model_name="gpt-3.5-turbo")
    chat_prompt = ChatPromptTemplate.from_messages(
        [system_message_prompt, human_message_prompt]
    )
    chain = LLMChain(llm=chat, prompt=chat_prompt)
    output = chain.run(
        style=style_input,
        brand=brand_name,
        style_product=product_style,
        number=hashtags_len,
        title_length=length_of_title,
        description_length=length_of_description,
        text=text_input,
    )

    split_data = output.split("\n")
    print(split_data)
    print(len(split_data))
    if len(split_data) == 3:
        title = split_data[0].replace("Title: ", "")
        desc = split_data[1].replace("Description: ", "")
        hasht = split_data[2].replace("Hashtags: ", "")

    elif len(split_data) == 5:
        title = split_data[0].replace("Title: ", "")
        desc = split_data[2].replace("Description: ", "")
        hasht = split_data[4].replace("Hashtags: ", "")
    else:
        title, desc, hasht = "", "", ""

    # title,description,seo=split_text(output)
    return title, desc, hasht
