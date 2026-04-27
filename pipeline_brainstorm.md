拿到一条序列之后，首先是使用运行跑MSA的脚本，去生成MSA。这一步需要跑各个方法默认的MSA流程，有的快有的慢。

所有脚本要注意前置条件和完成判断

需要自己跑一个二级结构预测流程，将预测好的二级结构统一输入给各个可以使用二级结构预测输入的方法

后处理？

pipeline中可以使用MSA作为输入的：
- NuFold：rMSA
- rhofold：轻量的MSA
- DeepFoldRNA：rMSA
- trRosettaRNA2：RNAcentral，轻量
- trRosettaRNA v1.1：需要自定义MSA
- RoseTTAFold2NA：阉割版rMSA
- alphafold3：轻量的MSA

pipeline中可以不使用MSA作为输入的：
- rhofold
- trRosettaRNA2
- DRfold2
- alphafold3
但是否影响精度有待考证

pipeline中输出预测的二级结构的：
- rhofold
- trRosettaRNA2

pipeline中使用预测二级结构特征的：
- NuFold：ipknot
- DeepFoldRNA：PETfold
- trRosettaRNA2：自己的pipeline，也支持自定义二级结构
- trRosettaRNA v1.1：SPOT-RNA，也支持自定义二级结构

有随机种子能生成多个model的：
- alphafold3
- ？


{target_name}/
- seq.fasta
- rMSA/
    - default/
        - seq/
            - seq.fasta
            - seq.a3m
- alphafold3/
    - default
        - seq.json
        - seq/
            - seq_data.json
            - msas/
            - models/
            - summary_confidences/
            - full_data/
- nufold/
    - default
        - seq/
            - seq.fasta
            - seq.a3m -> xxx
            - seq.ipknot.ss
            - modelxxx
- rhofold/
    - default
        - seq/
            - seq.fasta
            - seq.a3m
            - modelxxx
- trRNA/
    - default
        - seq/
            - seq.fasta
            - seq.a3m -> xxx
- trRNA2/
    - default
        - seq/
            - seq.fasta
            - seq.a3m
- drfold2/
    - default
        - seq/
            - seq.fasta
- rf2na/
    - default

