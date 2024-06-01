import board_functions
import json
import time
import pickle

# 第一次爬取
def firstSpider(defrost):
    # 读入配置文件
    cfg=""
    with open('./config/cfg.json', 'r') as f:
        cfg = json.load(f)
    # 获取提交数据

    print("spider for the first time")
    ans=board_functions.getSubmitList(cfg,True,defrost)

    # 写入字典文件
    dict={}
    for i in range(0,len(ans)):
        dict[ans[i]['submission_id']]=True
    with open("dict.pkl", "wb") as f:
        pickle.dump(dict, f)

    # 写入run文件
    with open("./data/run.json", 'w', encoding='utf-8') as file:
        json.dump(ans, file, ensure_ascii=False, indent=4)

    # 向board.xcpcio.com推送比赛数据
    res=board_functions.postToBoard(cfg)
    print(res)

# main函数
def spider(defrost):
    # 读入配置文件
    cfg=""
    with open('./config/cfg.json', 'r') as f:
        cfg = json.load(f)

    # 读入字典
    dict = {}
    with open("dict.pkl", "rb") as f:
        dict = pickle.load(f)
    # 隔一段时间获取一次数据，并推送给board
    i=0
    while True:
        writeRun=[]
        i=i+1
        if i==12:
            # 全部重新爬取
            i=0
            print("spider from start")

            # 获取提交数据
            ans=board_functions.getSubmitList(cfg,True,defrost)
            
            # 将之前没有处理的数据标记为已处理
            for j in range(0,len(ans)):
                if ans[j]['submission_id'] not in dict:
                    dict[ans[j]['submission_id']]=True
            writeRun=ans
        else:
            # 爬取增量数据
            print("spider from pre time")
            ans=board_functions.getSubmitList(cfg,False,defrost)
            # 获取本地测评记录
            files=board_functions.getJsonFiles()
            runData = json.loads(files['run.json'])
            # 加入新的测评记录
            for j in range(0,len(ans)):
                if ans[j]['submission_id'] not in dict:
                    dict[ans[j]['submission_id']]=True
                    runData.append(ans[j])
            writeRun=runData

        # 写入字典文件
        with open("dict.pkl", "wb") as f:
            pickle.dump(dict, f)

        # 写入run文件
        with open("./data/run.json", 'w', encoding='utf-8') as file:
            json.dump(writeRun, file, ensure_ascii=False, indent=4)

        # 向board.xcpcio.com推送比赛数据
        res=board_functions.postToBoard(cfg)
        print(res)
        time.sleep(60)


if __name__ == '__main__':
    firstSpider(False)
    spider(False)