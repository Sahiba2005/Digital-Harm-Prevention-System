function hideForms(){

document.getElementById("moneyForm").style.display="none"
document.getElementById("sensitiveForm").style.display="none"
document.getElementById("deleteForm").style.display="none"
document.getElementById("folderForm").style.display="none"
document.getElementById("linkForm").style.display="none"

}

function simulateAction(action){

let risk = Math.floor(Math.random()*100)

let decision=""

if(risk < 40){
decision="ALLOW"
}

else if(risk < 70){
decision="WARNING"
}

else{
decision="BLOCKED"
}

updateRisk(risk)

addLog(action,risk,decision)

}



function updateRisk(score){

document.getElementById("riskScore").innerText=
"Risk Score: "+score


let bar=document.getElementById("riskFill")

bar.style.width=score+"%"

if(score<40){
bar.style.background="green"
}

else if(score<70){
bar.style.background="orange"
}

else{
bar.style.background="red"
}

}



function addLog(action,risk,decision){

//alert("AI evaluated this action as: " + decision)

let table=document.getElementById("logTable")

let row=table.insertRow()

row.insertCell(0).innerText=new Date().toLocaleTimeString()

row.insertCell(1).innerText=action

row.insertCell(2).innerText=risk

row.insertCell(3).innerText=decision

}

function openMoneyForm(){

closeForms()

document.getElementById("moneyForm").style.display="flex"

}


function processMoney(){

let amount = document.getElementById("amount").value

let recipient = document.getElementById("recipient").value

let risk = 0

if(amount > 50000){
risk += 40
}

if(recipient.toLowerCase() === "unknown"){
risk += 40
}

risk += Math.floor(Math.random()*20)

let decision=""

if(risk < 40){
decision="ALLOW"
}
else if(risk < 70){
decision="WARNING"
}
else{
decision="BLOCKED"
}

updateRisk(risk)

addLog("Money Transfer",risk,decision)

document.getElementById("moneyResult").innerText =
"AI Decision: " + decision

}

function openSensitiveForm(){

closeForms()

document.getElementById("sensitiveForm").style.display="flex"

}



function scanSensitive(){

let text = document.getElementById("sensitiveText").value.toLowerCase()

let risk = 0

if(text.includes("password")){
risk += 40
}

if(text.includes("otp")){
risk += 40
}

if(text.includes("card")){
risk += 40
}

risk += Math.floor(Math.random()*20)

let decision = risk > 60 ? "BLOCKED" : "WARNING"

updateRisk(risk)

addLog("Sensitive Info Share",risk,decision)

document.getElementById("sensitiveResult").innerText =
"AI Decision: " + decision

}

function openDeleteForm(){

closeForms()

document.getElementById("deleteForm").style.display="flex"

}



function deleteFile(){

let file = document.getElementById("fileName").value

let risk = Math.floor(Math.random()*60)

let decision = risk > 40 ? "WARNING" : "ALLOW"

updateRisk(risk)

addLog("File Deletion",risk,decision)

document.getElementById("deleteResult").innerText =
"Deletion Status: " + decision

}

function openFolderForm(){

closeForms()

document.getElementById("folderForm").style.display="flex"

}

function checkFolderAccess(){

let password = document.getElementById("folderPassword").value

let risk = 0

if(password !== "secure123"){
risk = 70
}

let decision = risk > 50 ? "BLOCKED" : "ACCESS GRANTED"

updateRisk(risk)

addLog("Private Folder Access",risk,decision)

document.getElementById("folderResult").innerText =
decision

}

function openLinkForm(){

document.getElementById("linkForm").style.display="flex"

}



function scanURL(){

let url = document.getElementById("urlInput").value.toLowerCase()

let risk = 0

if(url.includes("free")){
risk += 30
}

if(url.includes("login")){
risk += 30
}

if(url.includes("verify")){
risk += 30
}

let decision = risk > 50 ? "PHISHING DETECTED" : "SAFE"

updateRisk(risk)

addLog("URL Scan",risk,decision)

document.getElementById("urlResult").innerText =
decision

}

function closeForms(){

document.getElementById("moneyForm").style.display="none"
document.getElementById("sensitiveForm").style.display="none"
document.getElementById("deleteForm").style.display="none"
document.getElementById("folderForm").style.display="none"
document.getElementById("linkForm").style.display="none"

}