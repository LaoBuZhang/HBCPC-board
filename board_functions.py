import urllib.request
import requests
import logging
import json
import gzip
import pickle
import board_utils


# 向pta发送请求时的header，不用变就行，直接从浏览器里粘贴来的
def getHeaders(cfg):
    # 从配置文件读取数据
    problemId=cfg['problemId']
    cookie=cfg['cookie']
    # 从浏览器复制的header
    headers={
        "Accept": "application/json;charset=UTF-8",
        "Accept-Encoding":"gzip, deflate, br, zstd",
        "Accept-Language":"zh-CN",
        "Cache-Control": "no-cache",
        "Content-Type": "application/json;charset=UTF-8",
        "Cookie": cookie,
        "Eagleeye-Pappname": "eksabfi2cn@94d5b8dc408ab8d",
        "Eagleeye-Sessionid": "3wlLtwL4j0X5772F1ymv1jt2bv0O",
        "Eagleeye-Traceid": "3f793bf1171646202705810238ab8d",
        "Pragma": "no-cache",
        "Priority": "u=1, i",
        "Referer": "https://pintia.cn/problem-sets/"+problemId+"/rankings",
        "Sec-Ch-Ua": '"Microsoft Edge";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
        "X-Lollipop": "fd0f671d1f29b275fdfb4df1999ef66a",
        "X-Marshmallow": ""
    }
    return headers


# 计算出提交时间距离开始时间的时间戳，单位为毫秒
def transTimeToTimestamp(judgeAt,startTimestamp):
    dt_object = board_utils.transTimeToTimestamp(judgeAt)
    timestamp = dt_object.timestamp()
    return (timestamp-startTimestamp)*1000


# 根据编译器信息得到语言，可以优化为使用配置文件
def transComplierToLanguage(compiler):
    if compiler=='GXX' or compiler=='CLANGXX':
        return "C++"
    elif compiler=='GCC' or compiler=='CLANG':
        return "C"
    elif compiler=='PYPY3' or compiler=='PYTHON3' or compiler=='PYTHON2':
        return "Python"
    elif compiler=='JAVAC':
        return "Java"
    else:
        return "Other Language"


# 将得到的提交记录转换为需要的格式
def transSubmit(submitList,problemList,defrost):
    # 此为pta请求到的格式
    # {
    #     "status": "WRONG_ANSWER",
    #     "team_id": "26",
    #     "problem_id": 12,
    #     "timestamp": 311820,
    #     "language": "C++",
    #     "submission_id": "787"
    # }

    # 读入config文件，获取比赛数据
    config="./config/config.json"
    with open(config, 'r', encoding='utf-8') as configFile:
        configData = json.load(configFile)
    startTimestamp=configData['start_time']*1000
    endTimestamp=configData['end_time']*1000
    frozenTimestamp=configData['frozen_time']*1000

    # 转换pta数据样式为board.xcpcio.com的样式
    responseSubmitList=[]
    for i in range(0,len(submitList)):
        submitRecord={}
        submitRecord['team_id']=submitList[i]['userId']
        submitRecord['problem_id']=ord(problemList[submitList[i]['problemSetProblemId']]['label'])-ord('A')
        submitRecord['timestamp']=transTimeToTimestamp(submitList[i]['judgeAt'],startTimestamp/1000)
        submitRecord['language']=transComplierToLanguage(submitList[i]['compiler'])
        submitRecord['submission_id']=submitList[i]['id']

        # https://github.com/xcpcio/xcpcio/blob/main/packages/libs/types/src/submission-status.ts
        # 有些提交信息pta中有，board中没有，例如下面的几个，需要特殊处理（否则的话在board上是Unknow，不会罚时），参考链接转换状态对应关系
        if endTimestamp-submitRecord['timestamp']-startTimestamp<=frozenTimestamp:
            submitRecord['status']='FROZEN'
        else:
            submitRecord['status']=submitList[i]['status']
            if submitList[i]['status']=="SEGMENTATION_FAULT" or submitList[i]['status']=="NON_ZERO_EXIT_CODE":
                submitRecord['status']="RUNTIME_ERROR"
            if submitList[i]['status']=="COMPILE_ERROR":
                submitRecord['status']="COMPILATION_ERROR"
        if defrost:
            submitRecord['status']=submitList[i]['status']
            if submitList[i]['status']=="SEGMENTATION_FAULT" or submitList[i]['status']=="NON_ZERO_EXIT_CODE":
                submitRecord['status']="RUNTIME_ERROR"
            if submitList[i]['status']=="COMPILE_ERROR":
                submitRecord['status']="COMPILATION_ERROR"
        submitRecord['timestamp']=int(submitRecord['timestamp'])
        responseSubmitList.append(submitRecord)
    return responseSubmitList


# pta的提交数据接口是分页查询，每次最多返回100条数据，即使limit设置更大也是100条，需要多次爬取下一页，才能得到所有数据
# 获取下一页的提交数据
def getNextSubmitList(cfg,id,ans,fromStart,defrost):
    # 从配置文件读取数据
    problemId=cfg['problemId']
    # 请求的链接
    url="https://pintia.cn/api/problem-sets/"+problemId+"/submissions?before="+id+"&limit=100&filter=%7B%7D"
    # 请求的header
    headers=getHeaders(cfg)
    # 发送请求
    req=urllib.request.Request(url,headers=headers)
    response=urllib.request.urlopen(req)
    # 解析请求
    content = gzip.decompress(response.read())
    data = content.decode('utf-8')
    json_data = json.loads(data)
    # 得到提交列表
    submitList=json_data['submissions']
    # 提交列表中涉及到的题目
    problemList=json_data['problemSetProblemById']
    # 提交列表中涉及到的用户的用户信息
    userList=json_data['examMemberByUserId']
    # 转换数据到board的格式
    ansNext=transSubmit(submitList,problemList,defrost)
    # 通过字典判断是否继续爬取
    # 继续爬取返回最后一条数据的id，作为下一次爬取的before参数的值
    # 不继续爬取则返回空字符串
    # fromStart表示是否从头开始爬取，正常爬取时只爬取新增数据（使用dict.pkl文件记录以爬取数据），每隔几次从头开始爬取，覆盖之前的数据，可以保证所有数据的正确性
    if not fromStart:
        dict = {}
        with open("dict.pkl", "rb") as f:
            dict = pickle.load(f)
        if len(ansNext)!=0:
            if ansNext[len(ansNext)-1]['submission_id'] in dict:
                ans.extend(ansNext)
                return ""
        else:
            return ""

    if len(ansNext)==0:
        return ""
    else:
        ans.extend(ansNext)
        return ansNext[len(ansNext)-1]['submission_id']
    



# 调用pta的接口得到提交列表
def getSubmitList(cfg,fromStart,defrost):
    # 从配置文件读取数据
    problemId=cfg['problemId']

    # 请求提交列表的url
    url="https://pintia.cn/api/problem-sets/"+problemId+"/submissions?limit=100&filter=%7B%7D"

    # 直接从浏览器复制的header
    headers=getHeaders(cfg)

    # 发送请求
    req=urllib.request.Request(url,headers=headers)
    response=urllib.request.urlopen(req)

    # 解析请求
    content = gzip.decompress(response.read())
    data = content.decode('utf-8')
    json_data = json.loads(data)

    # 得到提交列表
    submitList=json_data['submissions']
    # 提交列表中涉及到的题目
    problemList=json_data['problemSetProblemById']
    # 提交列表中涉及到的用户的用户信息
    userList=json_data['examMemberByUserId']

    # 转换数据到board的格式
    ans=transSubmit(submitList,problemList,defrost)


    # 通过字典判断是否继续爬取
    if not fromStart:
        dict = {}
        with open("dict.pkl", "rb") as f:
            dict = pickle.load(f)
        if len(ans)!=0:
            if ans[len(ans)-1]['submission_id'] in dict:
                return ans

    # 爬取后边页数
    id=""
    if len(ans)!=0:
        id=ans[len(ans)-1]['submission_id']
        id=getNextSubmitList(cfg,id,ans,fromStart,defrost)
        while id!="":
            id=getNextSubmitList(cfg,id,ans,fromStart,defrost)
    return ans

# 向board.xcpcio.com推送数据
def upload_to_xcpcio(cfg, files, url):
    payload = {
        "token": cfg['token'],
        "extra_files": files,
    }
    headers = {
        "content-type": "application/json",
    }
    resp = requests.post(url, json=payload, headers=headers)
    total_size = len(json.dumps(payload))

    logger = logging.getLogger(__name__)
    if resp.status_code == 200:
        logger.info("upload successful. [resp={}] [size={}]".format(
            resp.content, total_size))
    else:
        logger.error("upload failed. [status_code={}] [resp={}] [size={}]".format(
            resp.status_code, resp.text, total_size))

    return resp

# 读取配置文件
def getJsonFiles():
    # 读入config文件
    config="./config/config.json"
    with open(config, 'r', encoding='utf-8') as configFile:
        configData = json.load(configFile)
    configString = json.dumps(configData, ensure_ascii=False, indent=4)
    # 读入team文件
    team="./data/team.json"
    with open(team, 'r', encoding='utf-8') as teamFile:
        teamData = json.load(teamFile)
    teamString = json.dumps(teamData, ensure_ascii=False, indent=4)
    # 读入run文件
    run="./data/run.json"
    with open(run, 'r', encoding='utf-8') as runFile:
        runData = json.load(runFile)
    runString = json.dumps(runData, ensure_ascii=False, indent=4)
    files={}
    files['run.json']=runString
    files['config.json']=configString
    files['team.json']=teamString
    return files


# 向board推送数据
def postToBoard(cfg):
    # 向board.xcpcio.com推送比赛数据
    files=getJsonFiles()
    url="https://board-admin.xcpcio.com/upload-board-data"
    res=upload_to_xcpcio(cfg,files,url)
    return res


