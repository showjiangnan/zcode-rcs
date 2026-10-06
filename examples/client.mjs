import {RcsHttpClient,RcsRpcConnection} from '../sdk/index.js';
if (!process.env.RCS_ENDPOINT || !process.env.RCS_KEY) throw new Error('Set RCS_ENDPOINT and RCS_KEY; do not put credentials in a URL');
const http=new RcsHttpClient({endpoint:process.env.RCS_ENDPOINT});
let rpc,attachment;
try {
 await http.login(process.env.RCS_KEY,'Standalone integration');
 const devices=await http.listDevices();
 const device=devices.find(d=>d.id===process.env.RCS_DEVICE_ID)??devices[0];
 if (!device) throw new Error('No online desktop');
 const hosts=await http.listHosts(device.id),host=hosts[0],workspace=host?.workspaces[0];
 if (!workspace) throw new Error('No allowed workspace');
 attachment=await http.attach({deviceId:device.id,hostId:host.id,hostGeneration:host.generation,workspaceHandle:workspace.handle});
 rpc=await RcsRpcConnection.connect(http,attachment);
 const entries=await rpc.call({service:'file',method:'readdir',args:[{path:workspace.workspacePath}]});
 console.log({device:device.name,workspace:workspace.name,fileCount:entries.length,bridgeVersion:attachment.capabilities.bridgeVersion});
} finally {
 rpc?.dispose();if(attachment)await http.detach(attachment.id).catch(()=>{});await http.logout().catch(()=>{});
}
