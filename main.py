import asyncio
import os
import importlib.util
import json
import pytz
import traceback

from loguru import logger
from libs.common import call_duty
from libs.aws import AwsApi
from jinja2 import Environment, FileSystemLoader
from datetime import datetime

script_dir = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(script_dir, 'templates')
env = Environment(loader=FileSystemLoader(template_dir))
base_path = os.path.join(script_dir, 'check_scripts')
output_file_path = os.path.join(script_dir, 'output/output.html')
lock = asyncio.Lock()


async def process_file(file_path, file_name, folder, check_data):
    try:
        spec = importlib.util.spec_from_file_location(file_name[:-3], file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        if hasattr(module, 'run'):
            logger.info(f"Running module: {file_name}")
            result = await asyncio.to_thread(module.run)
            load_result = json.loads(result)

            # 加锁，避免出现覆盖现象
            async with lock:
                if isinstance(load_result, dict):
                    load_result = [load_result]
                if isinstance(load_result, list):
                    for item in load_result:
                        cloud_product = item.get('cloud_product', '')
                        if cloud_product not in check_data[folder]:
                            check_data[folder][cloud_product] = []
                        check_data[folder][cloud_product].append(item)
    except Exception:
        tb = traceback.format_exc()
        logger.error(f'Error running {file_name}: {tb}')


async def data_summary():
    check_data = {}
    exclude_module = ['test.py', 'cvm_snapshots_check.py']

    tasks = []

    for folder in os.listdir(base_path):
        folder_path = os.path.join(base_path, folder)
        # folder_path = 'check_scripts/global'
        # print(folder_path)
        if os.path.isdir(folder_path):
            check_data[folder] = {}

            for file_name in os.listdir(folder_path):
                if file_name.endswith('.py') and file_name not in exclude_module:
                    # if file_name.endswith('.py') and file_name == 'cloud_user_used_check.py':
                    file_path = os.path.join(folder_path, file_name)
                    tasks.append(process_file(file_path, file_name, folder, check_data))

    await asyncio.gather(*tasks)
    print(check_data)
    return check_data


def run():
    all_check_data = asyncio.run(data_summary())
    client = AwsApi()
    # print(all_check_data)
    cloud_sections = ''
    for cloud_title, cloud_products in all_check_data.items():
        cloud_sections += f'<div class="cloud-section" id="{cloud_title}-section">\n'
        cloud_sections += f'    <div class="cloud-title">{cloud_title.upper()}\n'
        cloud_sections += f'        <button class="toggle-button" onclick="toggleVisibility(\'cloud-content-{cloud_title}\')">收起</button>\n'
        cloud_sections += f'    </div>\n'
        cloud_sections += f'    <div id="cloud-content-{cloud_title}">\n'
        for cloud_product, checks in cloud_products.items():
            cloud_sections += f'        <div class="product-card">\n'
            cloud_sections += f'        <div class="product-title">{cloud_product}</div>\n'
            for iterm in checks:
                template = env.get_template(iterm['template'])
                cloud_sections += template.render(iterm=iterm)
            cloud_sections += f'        </div>\n'
        cloud_sections += f'    </div>\n'
        cloud_sections += f'</div>\n'

    base_template = env.get_template('base.html')
    output = base_template.render(cloud_sections=cloud_sections)

    with open(output_file_path, 'w', encoding='utf-8') as f:
        f.write(output)

    timezone = pytz.timezone('Asia/Shanghai')
    current_time = datetime.now(timezone).strftime('%Y%m%d')
    s3_key = current_time + '.html'
    client.upload_file_to_s3(output_file_path, 'devops-cloud-check-scripts.centurygame.com', s3_key)

    html_url = 'http://devops-cloud-check-scripts.centurygame.com/' + s3_key
    call_duty(html_url, "aws_check_cloud_report", "aws_check_cloud_report")
    logger.info("Generate report complete")


if __name__ == '__main__':
    run()
