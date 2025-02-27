代码结构说明：
    check_scripts:
        存放巡检项脚本，每一个巡检项一个脚本，放到对应的cloud目录中，如有新增的cloud即页面中蓝色的横条，直接在同级目录下创建目录即可，会将目录名称转换为大写字母渲染到页面中，无需更改前端部分
    libs:
        脚本中引用的函数方法
    output:
        最终生成的html文件
    templates:
        渲染模版
    main.py:
        启动文件

模版使用格式
1、template_1.html:
    {
        'template': 'template_1.html',
        'cloud_product': 'EC2',
        'category': 'no monitor ec2',
        'logic': '检查出标签prometheus:monitor为false的ec2实例',
        'results': []
    }
2、template_2.html:
    {
        'template': 'template_2.html',
        'product_title': 'prometheus'
        'header': ['field_1','field_2','field_3','field_4'],
        'row': [{'field_1':'value_1','field_2':'value_2','field_3':'value_3','faild_4':'value_4'}]
    }