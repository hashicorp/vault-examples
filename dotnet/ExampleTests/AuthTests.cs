using Microsoft.VisualStudio.TestTools.UnitTesting;
using Examples;

namespace ExampleTests
{
    [TestClass]
    public class AuthTests
    {
        const string ExpectedPwd = "Hashi123";

        [TestMethod]
        public void TokenAuthTest()
        {
            TokenAuthExample tokenAuthEx = new TokenAuthExample();
            
            var secretPwd = tokenAuthEx.GetSecretWithToken();
            Assert.AreEqual(ExpectedPwd, secretPwd);             
        }

        [TestMethod]
        public void AppRoleAuthTest()
        {
            ApproleAuthExample appRoleAuthEx = new ApproleAuthExample();

            var secretPwd = appRoleAuthEx.GetSecretWithAppRole();
            Assert.AreEqual(ExpectedPwd, secretPwd);             
        }
    }
}
