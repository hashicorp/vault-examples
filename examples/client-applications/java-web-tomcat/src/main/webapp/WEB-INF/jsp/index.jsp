<%@ page language="java" contentType="text/html; charset=UTF-8" pageEncoding="UTF-8"%>
<%@ taglib prefix="c" uri="http://java.sun.com/jsp/jstl/core" %>
<%@ taglib prefix="fmt" uri="http://java.sun.com/jsp/jstl/fmt" %>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vault Tomcat Web App</title>
    <link rel="stylesheet" href="${pageContext.request.contextPath}/css/style.css">
    <script>
        // Auto refresh (every 30 seconds)
        setInterval(function() {
            location.reload();
        }, 30000);
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Vault Tomcat Web App</h1>
            <p>Vault-integrated Java Web Application running on Tomcat 10</p>
        </div>

        <div class="auto-refresh">
            <p>🔄 Auto refresh: Page will automatically refresh every 30 seconds</p>
            <button class="refresh-btn" onclick="location.reload()">Manual Refresh</button>
            <a href="${pageContext.request.contextPath}/refresh" class="refresh-btn">Refresh Secrets</a>
        </div>

        <c:if test="${not empty error}">
            <div class="section">
                <h3>❌ Error Occurred</h3>
                <div class="secret-item error">
                    <strong>Error Message:</strong> <span>${error}</span>
                </div>
            </div>
        </c:if>

        <c:if test="${not empty vaultError}">
            <div class="section">
                <h3>⚠️ Vault Error</h3>
                <div class="secret-item error">
                    <strong>Vault Error:</strong> <span>${vaultError}</span>
                </div>
            </div>
        </c:if>

        <!-- Servlet Test Data -->
        <c:if test="${not empty testData}">
            <div class="section">
                <h3>🧪 Servlet Test Data</h3>
                <div class="secret-item">
                    <h4>Static Data Test</h4>
                    <p><strong>Message:</strong> <span>${testData.message}</span></p>
                    <p><strong>Time:</strong> <span>${testData.timestamp}</span></p>
                    <p><strong>Status:</strong> <span>${testData.status}</span></p>
                </div>
            </div>
        </c:if>

        <!-- Vault Secret Information -->
        <div class="section">
            <h3>🔐 Vault Secret Information</h3>
            
            <c:if test="${not empty secrets}">
                <c:forEach var="entry" items="${secrets}">
                    <div class="secret-item">
                        <h4>${entry.value.type} - ${entry.value.path}</h4>
                        <p><strong>Last Updated:</strong> <span><fmt:formatDate value="${entry.value.lastUpdated}" pattern="yyyy-MM-dd HH:mm:ss"/></span></p>
                        <c:if test="${not empty entry.value.version}">
                            <p><strong>Version:</strong> <span>${entry.value.version}</span></p>
                        </c:if>
                        <c:if test="${not empty entry.value.ttl}">
                            <p><strong>TTL:</strong> <span>${entry.value.ttl}</span> seconds</p>
                        </c:if>
                        <c:if test="${not empty entry.value.leaseId}">
                            <p><strong>Lease ID:</strong> <span>${entry.value.leaseId}</span></p>
                        </c:if>
                        <p><strong>Renewable:</strong> <span>${entry.value.renewable ? 'Yes' : 'No'}</span></p>
                        
                        <div class="secret-data">
                            <c:forEach var="dataEntry" items="${entry.value.data}" varStatus="status">
                                <strong>${dataEntry.key}</strong>: 
                                <c:choose>
                                    <c:when test="${not empty dataEntry.value}">
                                        <span>${dataEntry.value}</span>
                                    </c:when>
                                    <c:otherwise>
                                        <span style="color: #999; font-style: italic;">(empty)</span>
                                    </c:otherwise>
                                </c:choose>
                                <c:if test="${!status.last}"> | </c:if>
                            </c:forEach>
                        </div>
                    </div>
                </c:forEach>
            </c:if>
        </div>

        <!-- Database Connection Information -->
        <div class="section">
            <h3>🗄️ Database Connection Information</h3>
            
            <c:if test="${not empty dbConnection}">
                <div class="table-info">
                    <h4>Connection Status</h4>
                    <p><strong>Status:</strong> 
                        <span class="${dbConnection.status == 'success' ? 'status-success' : 'status-error'}">
                            ${dbConnection.status == 'success' ? '✅ Connection Successful' : '❌ Connection Failed'}
                        </span>
                    </p>
                    <c:if test="${dbConnection.status == 'success'}">
                        <p><strong>Database:</strong> <span>${dbConnection.database_product} ${dbConnection.database_version}</span></p>
                        <p><strong>Driver:</strong> <span>${dbConnection.driver_name} ${dbConnection.driver_version}</span></p>
                        <p><strong>URL:</strong> <span>${dbConnection.url}</span></p>
                        <p><strong>User:</strong> <span>${dbConnection.username}</span></p>
                    </c:if>
                    <c:if test="${dbConnection.status == 'error'}">
                        <p><strong>Error:</strong> <span>${dbConnection.error}</span></p>
                    </c:if>
                </div>
            </c:if>
        </div>

        <!-- Database Statistics -->
        <c:if test="${not empty dbStats}">
            <div class="section">
                <h3>📊 Database Statistics</h3>
                <div class="table-info">
                    <p><strong>Max Connections:</strong> <span>${dbStats.max_connections}</span></p>
                    <p><strong>Max Columns per Table:</strong> <span>${dbStats.max_columns_in_table}</span></p>
                    <p><strong>Max Columns per Index:</strong> <span>${dbStats.max_columns_in_index}</span></p>
                    <p><strong>Max Columns in SELECT:</strong> <span>${dbStats.max_columns_in_select}</span></p>
                    <p><strong>Total Tables:</strong> <span>${dbStats.table_count}</span></p>
                </div>
            </div>
        </c:if>

        <div class="timestamp">
            <p>Page Load Time: <span><fmt:formatDate value="<%=new java.util.Date()%>" pattern="yyyy-MM-dd HH:mm:ss"/></span></p>
        </div>
    </div>
</body>
</html>
