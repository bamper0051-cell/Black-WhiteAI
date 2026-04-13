
(function(){

let visible = true;

async function load(src){
  return new Promise((resolve, reject)=>{
    const s=document.createElement('script');
    s.src=src;
    s.onload=resolve;
    s.onerror=reject;
    document.head.appendChild(s);
  });
}

async function initLibs(){
  if(!window.React) await load("https://unpkg.com/react@18/umd/react.production.min.js");
  if(!window.ReactDOM) await load("https://unpkg.com/react-dom@18/umd/react-dom.production.min.js");

  const css=document.createElement("link");
  css.rel="stylesheet";
  css.href="https://unpkg.com/reactflow/dist/style.css";
  document.head.appendChild(css);

  if(!window.ReactFlow) await load("https://unpkg.com/reactflow/dist/reactflow.umd.js");
}

function createRoot(){
  const root=document.createElement("div");
  root.id="ai-builder";
  Object.assign(root.style,{
    position:"fixed",
    top:0,left:0,
    width:"100vw",
    height:"100vh",
    background:"#0a0a0a",
    zIndex:999999,
    display:"flex"
  });
  document.body.appendChild(root);
  return root;
}

function App(){
  const {useState,useCallback} = React;
  const {
    ReactFlow,
    Background,
    Controls,
    MiniMap,
    addEdge,
    useNodesState,
    useEdgesState
  } = window.ReactFlow;

  const [nodes,setNodes,onNodesChange]=useNodesState([]);
  const [edges,setEdges,onEdgesChange]=useEdgesState([]);
  const [logs,setLogs]=useState([]);
  const [task,setTask]=useState("");

  const onConnect = useCallback((params)=>setEdges(eds=>addEdge(params,eds)), []);

  function addNode(type){
    setNodes(nds=>nds.concat([{
      id:Date.now().toString(),
      position:{x:250,y:200},
      data:{label:type},
      style:{background:"#111",color:"#fff",padding:10,borderRadius:10}
    }]));
  }

  function highlight(id,status){
    setNodes(nds=>nds.map(n=>{
      if(n.id!==id) return n;
      return {
        ...n,
        style:{
          ...n.style,
          border:
            status==="active"?"2px solid yellow":
            status==="done"?"2px solid green":
            "2px solid red"
        }
      }
    }));
  }

  function stream(job_id){
    const ev=new EventSource(`/api/jobs/${job_id}/stream`);
    ev.onmessage=e=>{
      try{
        const msg=JSON.parse(e.data);
        if(msg.type==="node_start") highlight(msg.node,"active");
        if(msg.type==="node_done") highlight(msg.node,"done");
        if(msg.type==="error") highlight(msg.node,"error");
        setLogs(l=>l.concat([JSON.stringify(msg)]));
      }catch(_){}
    };
  }

  async function run(){
    const pipeline={
      nodes:nodes.map(n=>({id:n.id,type:n.data.label})),
      edges
    };

    const res=await fetch("/api/matrix/run",{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({pipeline,task})
    });
    const {job_id}=await res.json();
    stream(job_id);
  }

  async function aiBuild(){
    const res=await fetch("/api/pipeline/generate",{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({task})
    });
    const data=await res.json();

    if(data.nodes){
      setNodes(data.nodes.map(n=>({
        id:n.id,
        position:{x:150+Math.random()*300,y:150+Math.random()*200},
        data:{label:n.type},
        style:{background:"#111",color:"#fff",padding:10,borderRadius:10}
      })));
    }
    if(data.edges){
      setEdges(data.edges.map(e=>({
        id:e.from+"-"+e.to,
        source:e.from,
        target:e.to
      })));
    }
  }

  return React.createElement("div",{style:{display:"flex",width:"100%"}},

    // LEFT
    React.createElement("div",{style:{width:"220px",background:"#111",padding:"10px"}},
      ["planner","coder","executor","critic","fixer"].map(a=>
        React.createElement("div",{
          key:a,
          onClick:()=>addNode(a),
          style:{padding:"8px",marginBottom:"6px",background:"#222",cursor:"pointer"}
        },a)
      )
    ),

    // CENTER
    React.createElement("div",{style:{flex:1}},
      React.createElement(ReactFlow,{
        nodes,edges,onConnect,onNodesChange,onEdgesChange
      },
        React.createElement(Background,null),
        React.createElement(MiniMap,null),
        React.createElement(Controls,null)
      )
    ),

    // RIGHT
    React.createElement("div",{style:{width:"300px",background:"#111",padding:"10px",display:"flex",flexDirection:"column"}},
      React.createElement("input",{
        placeholder:"Задача...",
        value:task,
        onChange:e=>setTask(e.target.value)
      }),
      React.createElement("button",{onClick:aiBuild},"🧠 Build"),
      React.createElement("button",{onClick:run},"▶ Run"),
      React.createElement("div",{style:{flex:1,overflow:"auto",fontSize:"11px",marginTop:"10px"}},
        logs.map((l,i)=>React.createElement("div",{key:i},l))
      )
    )
  );
}

window.AIOverlay={
  init:async(opts={})=>{
    await initLibs();
    const root=createRoot();
    ReactDOM.createRoot(root).render(React.createElement(App));

    document.addEventListener("keydown",e=>{
      if(e.key=== (opts.hotkey||"F2")){
        visible=!visible;
        root.style.display = visible?"flex":"none";
      }
    });
  }
};

})();
